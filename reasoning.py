import logging

import time

from pyshacl import validate
from pyshacl.pytypes import GraphLike
import rdflib

from rdflib.namespace import OWL, RDF, RDFS

from pyshacl.shapes_graph import ShapesGraph

from typing import Dict, Iterator, List, Optional, Set, Tuple, Union, cast
from rdflib import BNode, Literal, URIRef

from pyshacl.monkey import apply_patches, rdflib_bool_patch, rdflib_bool_unpatch
from pyshacl.rdfutil import (
    clone_blank_node,
    clone_graph,
    compare_blank_node,
    compare_node,
    load_from_source,
    mix_datasets,
    mix_graphs,
    order_graph_literal,
)



shapes_graph = '''
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix schema: <http://schema.org/> .
@prefix owl: <http://www.w3.org/2002/07/owl#>. 
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

schema:PersonShape
    a sh:NodeShape ;
    sh:targetClass schema:Person ;
    sh:property [
        sh:path schema:givenName ;
        sh:datatype xsd:string ;
        sh:name "given name" ;
    ] ;
    sh:property [
        sh:path schema:birthDate ;
        sh:lessThan schema:deathDate ;
        sh:maxCount 1 ;
    ] ;
    sh:property [
        sh:path schema:gender ;
        sh:in ( "female" "male" ) ;
        sh:minCount 1 ;
    ] ;
    sh:property [
        sh:path schema:address ;
        sh:node schema:AddressShape ;
    ] .
schema:AddressShape
    a sh:NodeShape ;
    sh:property [
        sh:path schema:streetAddress ;
        sh:datatype xsd:string ;
    ] ;
    sh:property [
        sh:path schema:postalCode ;
        sh:or ( [ sh:datatype xsd:string ] [ sh:datatype xsd:integer ] ) ;
        sh:minInclusive 10000 ;
        sh:maxInclusive 99999 ;
    ] .
'''
shapes_graph_format = 'turtle'

data_graph = '''
@prefix : <http://example.org/ns#> .
@prefix dash: <http://datashapes.org/dash#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix schema: <http://schema.org/> .
@prefix owl: <http://www.w3.org/2002/07/owl#>. 
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

:alice schema:gender "female".

:alili schema:address [ schema:streetAddress "1600 Amphitheatre Pkway"].

:Alice schema:givenName "ALICE";
       owl:sameAs :alili;
       owl:sameAs :alice.

:ali a schema:Person ;
     schema:address [ schema:postalCode 9404] ;
     owl:sameAs :alice.      
     
:simon a schema:Student;
       schema:know :alice.

:semon owl:sameAs :simon.

:Math a schema:Department.

:math owl:sameAs :Math.

:CS a schema:Department.

:info owl:sameAs :CS.

schema:Student rdfs:subClassOf schema:Person.
'''
data_graph_format = 'turtle'


def reasoning(
    data_graph: Union[GraphLike, str, bytes],
    *args,
    shacl_graph: Optional[Union[GraphLike, str, bytes]] = None,
    data_graph_format: Optional[str] = None,
    shacl_graph_format: Optional[str] = None,
    **kwargs,):
    
    #data_graph_format = kwargs.pop('data_graph_format', None)
    # force no owl imports on data_graph
    loaded_dg = load_from_source(data_graph, rdf_format=data_graph_format, multigraph=True, do_owl_imports=False)
    if not isinstance(loaded_dg, rdflib.Graph):
        raise RuntimeError("data_graph must be a rdflib Graph object")
   
    data_graph_is_multigraph = isinstance(loaded_dg, (rdflib.Dataset, rdflib.ConjunctiveGraph))
    
    #shacl_graph_format = kwargs.pop('shacl_graph_format', None)
    if shacl_graph is not None:
        rdflib_bool_patch()
        loaded_sg = load_from_source(
            shacl_graph, rdf_format=shacl_graph_format, multigraph=True, do_owl_imports=False)
        rdflib_bool_unpatch()
    else:
        loaded_sg = None
        
    assert isinstance(loaded_sg, rdflib.Graph), "shacl_graph must be a rdflib Graph object"
    shape_graph = ShapesGraph(loaded_sg, None)  # type: ShapesGraph
    
    shapes = shape_graph.shapes  # This property getter triggers shapes harvest.
       
    the_target_graph = loaded_dg
    if isinstance(the_target_graph, (rdflib.Dataset, rdflib.ConjunctiveGraph)):
        named_graphs = [
            rdflib.Graph(the_target_graph.store, i, namespace_manager=the_target_graph.namespace_manager)
            if not isinstance(i, rdflib.Graph)
            else i
            for i in the_target_graph.store.contexts(None)
        ]
    else:
        named_graphs = [the_target_graph]
    

    for g in named_graphs:
        vg = g 
        found_node_targets = set()
        for s in shapes:
            focus = s.focus_nodes(g)
            found_node_targets.update(focus)
            
        for focus_node in found_node_targets:      
            while not all_merged(vg, focus_node):
                merge_same_node(vg, focus_node)
                           
    return vg

def all_merged(g, focus):
    
    for o in g.objects(focus, OWL.sameAs):   #focus node = o
        if o != focus:  
            m1 = [(pp, oo) for pp, oo in g.predicate_objects(o)] # o pp oo exists
            if len(m1)!= 0:
                return False
    m2 = [s for s in g.subjects(OWL.sameAs, focus)] # s = focus exists
    if len(m2) != 0:
        return False             
    return True
        

def merge_same_node(g, focus):
    for s in g.subjects(OWL.sameAs, focus): # s = focus node
        if s != focus:
            g.remove((s, OWL.sameAs, focus))
            g.add((focus, OWL.sameAs, s)) # s = focus --> focus = s
            
            for ss in g.subjects(OWL.sameAs, s): # ss = s --> focus = ss
                if ss != focus:
                    g.remove((ss, OWL.sameAs, s)) 
                    g.add((focus, OWL.sameAs, ss))
            for oo in g.objects(s, OWL.sameAs): # s = oo --> focus = oo
                if oo != focus:
                    g.remove((s, OWL.sameAs, oo))
                    g.add((focus, OWL.sameAs, oo))
                            
            
    for o in g.objects(focus, OWL.sameAs): #focus node = o
        if o != focus: 
            for z in g.objects(o, OWL.sameAs): # o = z --> focus = z
                if z != focus:
                    g.remove((o, OWL.sameAs, z)) # remove o = z
                    g.add((focus, OWL.sameAs, z)) # add focus node = z
                    
            for z in g.subjects(OWL.sameAs, o): # z = o -->  focus = z
                if z != focus:
                    g.remove((z, OWL.sameAs, o))
                    g.add((focus, OWL.sameAs, z))
    
    for o in g.objects(focus, OWL.sameAs):   #focus node = o
        if o != focus:  
            for pp, oo in g.predicate_objects(o): # o pp oo --> focus pp oo
                g.add((focus, pp, oo))
                g.remove((o, pp, oo))  
            for ss, pp in g.subject_predicates(o): # ss pp o --> ss pp fucus
                
                if ss != focus:
                    g.add((ss, pp, focus))
                    g.remove((ss, pp, o))
    
'''    
time_start =time.time()    
conforms, v_graph, v_text = validate(data_graph, shacl_graph=shapes_graph,
                                     data_graph_format=data_graph_format,
                                     shacl_graph_format=shapes_graph_format,
                                     inference='both')  
time_end=time.time() 
print('time cost: ', (time_end-time_start)*1000)

time_start1 =time.time()
list = reasoning(data_graph, shacl_graph=shapes_graph,data_graph_format='turtle',shacl_graph_format='turtle')


conforms1, v_graph1, v_text1 = validate(list, shacl_graph=shapes_graph,
                                     data_graph_format=data_graph_format,
                                     shacl_graph_format=shapes_graph_format,
                                     inference='none')
time_end1=time.time()

print('time cost1: ', (time_end1-time_start1)*1000)

print(list.serialize(format="turtle"))

print(v_text)
print(v_text1)
'''