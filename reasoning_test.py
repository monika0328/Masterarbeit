from fused_graph import fused_graph, noiseless_fused_graph
import time
from pyshacl import validate

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
        sh:path schema:Name ;
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
    sh:closed true ;
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


:alice schema:nn "Alice";
       schema:gender "female".

:Alice schema:name "Alice".
       
schema:name owl:sameAs schema:Name.

schema:nn owl:sameAs schema:name.

schema:nn a owl:InverseFunctionalProperty.

:ali a schema:Person; 
     schema:address [ schema:streetAddress "1600 Amphitheatre Pkway"; schema:postalCode 94004] ;
     owl:sameAs :alice.      
     
:simon a schema:Student;
       schema:knows :alice.

:semon owl:sameAs :simon.

schema:TL rdfs:subClassOf schema:Person.

schema:Student owl:equivalentClass schema:TL.

:math a schema:Course;
      schema:name "Math".

'''
data_graph_format = 'turtle'



#"""  
print("Example !!! TEST for owl:InverseFunctionalProperty and rdfs:domain !!!")

t1=time.time()    
conform, v_g, v_t = validate(data_graph, shacl_graph=shapes_graph,
                                     data_graph_format='turtle',
                                     shacl_graph_format=shapes_graph_format,
                                     inference='none')  
t2=time.time() 
print('Runtime: ', (t2-t1)*1000, 'ms [without]')

time_start =time.time()    
conforms, v_graph, v_text = validate(data_graph, shacl_graph=shapes_graph,
                                     data_graph_format='turtle',
                                     shacl_graph_format=shapes_graph_format,
                                     inference='both')  
time_end=time.time() 
print('Runtime: ', (time_end-time_start)*1000, 'ms [Naive method]')



time_start1 =time.time()
vali_graph, same_g = fused_graph(data_graph, shacl_graph=shapes_graph,data_graph_format='turtle',shacl_graph_format='turtle')
conforms1, v_graph1, v_text1 = validate(vali_graph, shacl_graph=shapes_graph,
                                     data_graph_format=data_graph_format,
                                     shacl_graph_format=shapes_graph_format,
                                     inference='none')
time_end1=time.time()


time_start2 =time.time()
v_graph, same_list = noiseless_fused_graph(data_graph, shacl_graph=shapes_graph,data_graph_format='turtle',shacl_graph_format='turtle',merge_Type=True)
conforms2, v_graph2, v_text2 = validate(v_graph, shacl_graph=shapes_graph,
                                     data_graph_format=data_graph_format,
                                     shacl_graph_format=shapes_graph_format,
                                     inference='none')
time_end2=time.time()

time_start3 =time.time()
v_graph2, same_list2 = noiseless_fused_graph(data_graph, shacl_graph=shapes_graph,data_graph_format='turtle',shacl_graph_format='turtle',merge_Type=False)
conforms3, v_graph3, v_text3 = validate(v_graph2, shacl_graph=shapes_graph,
                                     data_graph_format=data_graph_format,
                                     shacl_graph_format=shapes_graph_format,
                                     inference='none')
time_end3=time.time()


print('Runtime: ', (time_end1-time_start1)*1000, 'ms [Fused Graph]')

print('Runtime: ', (time_end2-time_start2)*1000, 'ms [Noiseless Fused Graph by removing nodes]')

print('Runtime: ', (time_end3-time_start3)*1000, 'ms [Noiseless Fused Graph by adding nodes]')


print("===================Fused Graph=====================")
print(vali_graph.serialize(format="turtle"))
print("======================End==========================\n")

print("All same focus nodes: ")
print(same_g)
print("\n")

print("===============Noiseless Fused Graph=================")
print(v_graph.serialize(format="turtle"))
print("=======================End===========================\n")


print("===============Noiseless Fused Graph 2=================")
print(v_graph2.serialize(format="turtle"))
print("=======================End===========================\n")


print("=======================Reports===========================\n")
print(v_t)
print(v_text)
print(v_text1)
print(v_text2)
print(v_text3)
#"""