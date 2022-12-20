
from errors import FusionRuntimeError
from pyshacl.pytypes import GraphLike
import rdflib

from rdflib.namespace import OWL, RDF, RDFS

from pyshacl.shapes_graph import ShapesGraph

from typing import TYPE_CHECKING, Dict, Iterator, List, Optional, Set, Tuple, Union, cast
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
from pyshacl.consts import (
    SH_path,
    RDFS_subClassOf,
)

if TYPE_CHECKING:
    from pyshacl.constraints import ConstraintComponent
    from pyshacl.shapes_graph import ShapesGraph


def load_graph(data_graph: Union[GraphLike, str, bytes],
    shacl_graph: Optional[Union[GraphLike, str, bytes]] = None,
    data_graph_format: Optional[str] = None,
    shacl_graph_format: Optional[str] = None,
    ):
    
    loaded_dg = load_from_source(data_graph, rdf_format=data_graph_format, multigraph=True, do_owl_imports=False)
    if not isinstance(loaded_dg, rdflib.Graph):
        raise RuntimeError("data_graph must be a rdflib Graph object")

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
        
    return shapes, named_graphs
    
    

def fused_graph(
    data_graph: Union[GraphLike, str, bytes],
    shacl_graph: Optional[Union[GraphLike, str, bytes]] = None,
    data_graph_format: Optional[str] = None,
    shacl_graph_format: Optional[str] = None,
    ):
    
    shapes, named_graphs = load_graph( data_graph, shacl_graph, data_graph_format,shacl_graph_format)    

    for g in named_graphs:
        vg = g 
        found_node_targets = set()
        target_classes = set()
        path_value = set()
        found_target_classes = set()
        for s in shapes:
            focus = s.focus_nodes(vg)
            found_node_targets.update(focus)
            target_classes.update(s.target_classes())
            target_classes.update(s.implicit_class_targets())
                
            target_property=set(s.property_shapes())            
            for blin in target_property:
                path_value.update(s.sg.graph.objects(blin, SH_path))
        
        for tc in target_classes:
            subc = vg.transitive_subjects(RDFS_subClassOf, tc)
            for subclass in subc:
                if subclass == tc:
                    continue
                found_target_classes.add(subclass)
        target_classes.update(found_target_classes)
        
        merge_eq_classes(vg, found_node_targets, target_classes)
        
        # merge same properties 
        merge_same_property(vg, path_value, found_node_targets, target_classes)
        
        same_nodes = dict()
        for f in found_node_targets:
            same_set = set()
            same_nodes.update({f: same_set})
        
        # merge same nodes
        for focus_node in found_node_targets:      
            while not all_focus_merged(vg, focus_node):
                merge_same_focus(vg, same_nodes, focus_node)  
                check_com_dw(vg, target_classes)
                                   
    return vg, same_nodes

def check_symmetricProperty(g, p): # RULE prp-symp
    if (p, RDF.type, OWL.SymmetricProperty) in g:
        for x, y in g.subject_objects(p):
            g.add((y, p, x))
        g.remove((p, RDF.type, OWL.SymmetricProperty))
    

def check_asymmetricProperty(g, p): # prp-asyp
    if (p, RDF.type, OWL.AsymmetricProperty) in g:
        for x, y in g.subject_objects(p):
            if (y, p, x) in g:
                raise FusionRuntimeError(
                    "Erroneous usage of asymmetric property %s on %s and %s"
                    % (p, x, y)
                )
                
                
def check_propertyDisjointWith(g, focus_property): # prp-pdw
    for p in g.objects(focus_property, OWL.propertyDisjointWith):
        for x, y in g.subject_objects(focus_property):
            if (x, p, y) in g:
                raise FusionRuntimeError(
                    "Erroneous usage of disjoint properties %s and %s on %s and %s"
                    % (focus_property, p, x, y)
                )
    """
    for p in g.subjects(OWL.propertyDisjointWith, focus_property):
        for x, y in g.subject_objects(p):
            if (x, focus_property, y) in g:
                raise FusionRuntimeError(
                    "Erroneous usage of disjoint properties %s and %s on %s and %s"
                    % (p, focus_property, x, y)
                )
    """
    
def check_domain_range(g, p, target_nodes, target_classes):
    for o in g.objects(p, RDFS.domain): # RULE prp-dom
        if o in target_classes:
            for x, y in g.subject_objects(p):
                g.add((x, RDF.type, o))
                if not x in target_nodes:
                    target_nodes.add(x)

        else:
            for x, y in g.subject_objects(p):
                if x in target_nodes:
                    g.add((x, RDF.type, o))

    for o in g.objects(p, RDFS.range): # RULE prp-rng
        if o in target_classes:
            for x, y in g.subject_objects(p):
                g.add((y, RDF.type, o))
                if not y in target_nodes:
                    target_nodes.add(y)
        else:
            for x, y in g.subject_objects(p):
                if y in target_nodes:
                    g.add((y, RDF.type, o))
                    
    return target_nodes

def check_com_dw(g, class_list):
    for target_class in class_list:
        # RULE cls-com
        for c2 in g.objects(target_class, OWL.complementOf):
            for x in g.subjects(RDF.type, target_class):
                if (x, RDF.type, c2) in g:
                    raise FusionRuntimeError(
                        "Violation of complementarity for classes %s and %s on element %s (or an identical individual with it)"
                        % (target_class, c2, x)
                    )
                    
        for c1 in g.subjects(OWL.complementOf, target_class):
            for x in g.subjects(RDF.type, c1):
                if (x, RDF.type, target_class) in g:
                    raise FusionRuntimeError(
                        "Violation of complementarity for classes %s and %s on element %s (or an identical individual with it)"
                        % (c1, target_class, x)
                    )
    
        # RULE cax-dw 
        for c2 in g.objects(target_class, OWL.disjointWith):
            for x in g.subjects(RDF.type, target_class):
                if (x, RDF.type, c2) in g:
                    raise FusionRuntimeError(
                        "Disjoint classes %s and %s have a common individual %s (or an identical individual with it)"
                        % (target_class, c2, x)
                    )
                    
        for c1 in g.subjects(OWL.disjointWith, target_class):
            for x in g.subjects(RDF.type, c1):
                if (x, RDF.type, target_class) in g:
                    raise FusionRuntimeError(
                        "Disjoint classes %s and %s have a common individual %s (or an identical individual with it)"
                        % (c1, target_class, x)
                    )

    
    

def check_eq_diff_erro(g, s, o):
    if (s, OWL.differentFrom, o) in g or (
        o,
        OWL.differentFrom,
        s,
    ) in g:
        raise FusionRuntimeError(
                "'sameAs' and 'differentFrom' cannot be used on the same subject-object pair: (%s, %s)"
                    % (s, o)
            )
             
def check_irreflexiveProperty(g,p): # RULE prp-irp
    if (p, RDF.type, OWL.IrreflexiveProperty) in g:
        for x, y in g.subject_objects(p):
            if x == y:
                raise FusionRuntimeError(
                        "Irreflexive property used on %s with %s" % (x, p)
                    ) 

def all_property_merged(g, property):
    m1 = [o for o in g.objects(property, OWL.sameAs)]
    if len(m1)!= 0:
        return False
    m2 = [s for s in g.subjects(OWL.sameAs, property)] 
    if len(m2) != 0:
        return False             
    m3 = [oo for oo in g.objects(property, OWL.equivalentProperty)]
    if len(m3)!= 0:
        return False
    m4 = [ss for ss in g.subjects(OWL.equivalentProperty, property)] 
    if len(m4) != 0:
        return False 
    return True

def all_focus_merged(g, focus):

    m1 = [o for o in g.objects(focus, OWL.sameAs)] # focus node = o exists
    if len(m1)!= 0:
        return False
    m2 = [s for s in g.subjects(OWL.sameAs, focus)] # s = focus exists
    if len(m2) != 0:
        return False             
    return True

def check_FunctionalProperty(g, focus_property, found_node_targets):
    # prp-fp
    if (focus_property, RDF.type, OWL.FunctionalProperty) in g: 
        for x, y1 in g.subject_objects(focus_property):
            for y2 in g.objects(x, focus_property):
                if y1 != y2:
                    #if y1 in found_node_targets or y2 in found_node_targets:
                    g.add((y1, OWL.sameAs, y2))
        g.remove((focus_property, RDF.type, OWL.FunctionalProperty))
    
def check_InverseFunctionalProperty(g, focus_property, found_node_targets):
    # prp-ifp
    if (focus_property, RDF.type, OWL.InverseFunctionalProperty) in g:
        for x1, y in g.subject_objects(focus_property):
            for x2 in g.subjects(focus_property, y):
                if x1 != x2:
                    #if x1 in found_node_targets or x2 in found_node_targets:
                    g.add((x1, OWL.sameAs, x2))
        g.remove((focus_property, RDF.type, OWL.InverseFunctionalProperty))
        
def all_subProperties_merged(g, p):
    m1 = [s for s in g.subjects(RDFS.subPropertyOf, p)]
    if len(m1)!= 0:
        return False
    return True

def merge_eq_classes(g, found_node_targets, target_classes):
    eq_targetClass = set()
    eq_targetNodes = set()
    for c in target_classes:
        for c1 in g.subjects(OWL.equivalentClass, c): # c1 == c
            eq_targetClass.add(c1)
            for s in g.subjects(RDF.type, c1):
                eq_targetNodes.add(s)
                g.add((s, RDF.type, c))
            for ss in g.subjects(RDF.type, c):
                g.add((ss, RDF.type, c1))
            g.remove((c1, OWL.equivalentClass, c))
        for c2 in g.objects(c, OWL.equivalentClass): # c == c2
            eq_targetClass.add(c2)
            for s in g.subjects(RDF.type, c2):
                eq_targetNodes.add(s)
                g.add((s, RDF.type, c))
            for ss in g.subjects(RDF.type, c):
                g.add((ss, RDF.type, c2))
            g.remove((c, OWL.equivalentClass, c2))

    found_node_targets.update(eq_targetNodes)
    target_classes.update(eq_targetClass)   
    
            
        
def merge_same_property(g, properties, found_node_targets, target_classes):
    for focus_property in properties:
        check_irreflexiveProperty(g, focus_property)
        check_asymmetricProperty(g, focus_property)
        # subProperty
        while not all_subProperties_merged(g, focus_property):
            for sub_p in g.subjects(RDFS.subPropertyOf, focus_property):   
                if (focus_property, RDFS.subPropertyOf, sub_p) in g: #scm-eqp2
                    g.add((focus_property, OWL.sameAs, sub_p))
                else:
                    for p3 in g.subjects(RDFS.subPropertyOf, sub_p): # RULE scm-spo
                        if focus_property != p3:
                            g.add((p3, RDFS.subPropertyOf, focus_property))
                            
                    for c in g.objects(focus_property,RDFS.domain): #scm-dom2
                        g.add((sub_p, RDFS.domain, c))
                        
                    for c1 in g.objects(focus_property,RDFS.range): #scm-rng2
                        g.add((sub_p, RDFS.range, c1))
                        
                    for x, y in g.subject_objects(sub_p): # prp-spo1
                        g.add((x, focus_property, y))
                
                    g.remove((sub_p, RDFS.subPropertyOf, focus_property))
            
        
        while not all_property_merged(g, focus_property):
            for p1 in g.subjects(OWL.equivalentProperty, focus_property):
                g.remove((p1, OWL.equivalentProperty, focus_property))
                g.add((focus_property, OWL.sameAs, p1))
            for p2 in g.objects(focus_property, OWL.equivalentProperty):
                g.remove((focus_property, OWL.equivalentProperty, p2))
                g.add((focus_property, OWL.sameAs, p2))
            
            for same_prop in g.subjects(OWL.sameAs, focus_property):                 
                g.remove((same_prop, OWL.sameAs, focus_property))
                g.add((focus_property, OWL.sameAs, same_prop))
                
            for same_property in g.objects(focus_property, OWL.sameAs):
                check_irreflexiveProperty(g, same_property)
                check_asymmetricProperty(g, same_property)
                
                if same_property != focus_property:
                    if not same_property in properties:
                        for p, o in g.predicate_objects(same_property):
                            g.remove((same_property, p, o))
                            g.add((focus_property, p, o))
                        for s, p in g.subject_predicates(same_property):
                            g.remove((s, p, same_property))
                            g.add((s, p, focus_property))
                        for s, o in g.subject_objects(same_property):
                            g.add((s, focus_property, o))
                            g.remove((s, same_property, o))
                        
                    else:
                        for s, o in g.subject_objects(same_property):
                            if not (s, focus_property) in g.triples():
                                g.add((s, focus_property))
                            
                        for p, o in g.predicate_objects(same_property):
                            if not (focus_property, p, o) in g.triples():
                                g.add((focus_property, p, o))
                        for s, p in g.subject_predicates(same_property):
                            if not (s, p, focus_property) in g.triples():
                                g.add((s, p, focus_property))
                    
                g.remove((focus_property, OWL.sameAs, same_property))
            
                
        check_propertyDisjointWith(g, focus_property)
        check_symmetricProperty(g, focus_property)
        check_domain_range(g, focus_property, found_node_targets, target_classes)
        check_com_dw(g, target_classes)
        check_FunctionalProperty(g, focus_property, found_node_targets)
        check_InverseFunctionalProperty(g, focus_property, found_node_targets)
    #return found_node_targets    


def merge_same_focus(g, same_nodes, focus):
    #eq-sym
    for s in g.subjects(OWL.sameAs, focus): # s = focus node
        check_eq_diff_erro(g, s, focus)
        if s != focus:
            g.remove((s, OWL.sameAs, focus))
            g.add((focus, OWL.sameAs, s)) # s = focus --> focus = s
                            
    
    for o in g.objects(focus, OWL.sameAs):   #focus node = o
        check_eq_diff_erro(g, focus, o)
        if o != focus:  
            same_set = same_nodes[focus]
            same_set.add(o)
            if o in same_nodes:
                del same_nodes[o]
            # for "eq-trans", "eq-rep-s", "eq-rep-o"
            for pp, oo in g.predicate_objects(o): # o pp oo --> focus pp oo
                g.remove((o, pp, oo))  
                g.add((focus, pp, oo))
                '''
                if not isinstance(oo, BNode):
                    g.add((focus, pp, oo))
                else:
                    for bn in g.objects(focus, pp):
                        if isinstance(bn, BNode):
                            g.add((focus, pp, oo))
                '''
            for ss, pp in g.subject_predicates(o): # ss pp o --> ss pp fucus
                g.remove((ss, pp, o))
                g.add((ss, pp, focus))
                
        if o == focus:
            g.remove((focus, OWL.sameAs, focus))
         

def noiseless_fused_graph(
    data_graph: Union[GraphLike, str, bytes],
    shacl_graph: Optional[Union[GraphLike, str, bytes]] = None,
    data_graph_format: Optional[str] = None,
    shacl_graph_format: Optional[str] = None,
    merge_Type: bool=True,
    ):
    
    shapes, named_graphs = load_graph( data_graph, shacl_graph, data_graph_format,shacl_graph_format)    

    for g in named_graphs:
        vg = g 
        found_node_targets = set()
        target_classes = set()
        path_value = set()
        global_path = set()
        found_target_classes = set()
        for s in shapes:
            focus = s.focus_nodes(vg)
            found_node_targets.update(focus)
            target_classes.update(s.target_classes())
            target_classes.update(s.implicit_class_targets())
            
            target_property=set(s.property_shapes())

            if len(set(s.target_classes()))==0:       
                for blin in target_property:
                    global_path.update(s.sg.graph.objects(blin, SH_path))

            for blin in target_property:
                path_value.update(s.sg.graph.objects(blin, SH_path))

        for tc in target_classes:
            subc = vg.transitive_subjects(RDFS_subClassOf, tc)
            for subclass in subc:
                if subclass == tc:
                    continue
                found_target_classes.add(subclass)
        target_classes.update(found_target_classes)

        merge_eq_classes(vg, found_node_targets, target_classes)
            
        # merge same properties 
        merge_same_property(vg, path_value, found_node_targets, target_classes)
        
        
        same_nodes = dict()
        for f in found_node_targets:
            same_set = set()
            same_nodes.update({f: same_set})
            
        for focus_node in found_node_targets:      
            while not all_focus_merged(vg, focus_node):
                merge_same_focus(vg, same_nodes, focus_node)   
                check_com_dw(vg, target_classes)

        
        if merge_Type:
            for s, p, o in vg:
                if not p in global_path and (not s in found_node_targets.union(target_classes)):
                    vg.remove((s,p,o))
            return vg, same_nodes
        else:
            rg = rdflib.Graph()
            for p, n in vg.namespace_manager.namespaces():
                rg.namespace_manager.bind(p, n)
            
            #"""
            for s in found_node_targets.union(target_classes):
                for pp, oo in vg.predicate_objects(s):
                    rg.add((s, pp, oo))
            for p in global_path:
                for ss, oo in vg.subject_objects(p):
                    if not ss in found_node_targets.union(target_classes):
                        rg.add((ss, p, oo))
            return rg, same_nodes
            
            
            
          
 
  