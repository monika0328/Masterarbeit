from fused_graph import fused_graph, noiseless_fused_graph
import time
from pyshacl import validate


shapes_graph = '''
@prefix : <http://example.org/ns#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix schema: <http://schema.org/> .
@prefix owl: <http://www.w3.org/2002/07/owl#>. 
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

:UserShape a sh:NodeShape;
   sh:targetClass :User ;
   sh:property [                  # Blank node 1
    sh:path     schema:name ;
    sh:minCount 1;
    sh:maxCount 1;
    sh:datatype xsd:string ;
  ] ;
  sh:property [                   # Blank node 2
   sh:path schema:gender ;
   sh:minCount 1;
   sh:maxCount 1;
   sh:or (
    [ sh:in (schema:Male schema:Female) ]
    [ sh:datatype xsd:string]
   )
  ] ;
  sh:property [                   # Blank node 3  
   sh:path     schema:birthDate ;
   sh:maxCount 1;
   sh:datatype xsd:date ;
  ] ;
  sh:property [                   # Blank node 4 
   sh:path     schema:knows ;
   sh:nodeKind sh:IRI ;
   sh:class    :User ;
  ] .
'''


data_graph_0 = '''
@prefix : <http://example.org/ns#> .
@prefix dash: <http://datashapes.org/dash#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix schema: <http://schema.org/> .
@prefix owl: <http://www.w3.org/2002/07/owl#>. 
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

:alice a :User;                             #Passes as a :UserShape     
       schema:name           "Alice" ;
       schema:gender         schema:Female ;
       schema:knows          :bob .

:bob   a :User;                             #Passes as a :UserShape     
       schema:gender         schema:Male ;
       schema:name           "Robert";
       schema:birthDate      "1980-03-10"^^xsd:date .

:carol a :User;                             #Passes as a :UserShape     
       schema:name           "Carol" ;
       schema:gender         schema:Female ;
       foaf:name             "Carol" .
'''



data_graph_1 = '''
@prefix : <http://example.org/ns#> .
@prefix dash: <http://datashapes.org/dash#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix schema: <http://schema.org/> .
@prefix owl: <http://www.w3.org/2002/07/owl#>. 
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

:dave  a :User ;                        #Fails as a :UserShape     
       schema:name       "Dave";
       schema:gender     :Unknown ;
       schema:birthDate  1980 ;
       schema:knows      :grace .

:emily a :User ;                        #Fails as a :UserShape          
       schema:name       "Emily", "Emilee";
       schema:gender     schema:Female .

:frank a :User ;                        #Fails as a :UserShape     
       foaf:name         "Frank" ;
       schema:gender     schema:Male .

'''


time_start =time.time()    
conforms, v_graph, v_text = validate(data_graph_0, shacl_graph=shapes_graph,
                                     data_graph_format='turtle',
                                     shacl_graph_format='turtle',
                                     inference='both')  
time_end=time.time() 
print('Runtime for example without errors: ', (time_end-time_start)*1000, 'ms [Naive method]')



time_start1 =time.time()
vali_graph, same_g = fused_graph(data_graph_0, shacl_graph=shapes_graph,data_graph_format='turtle',shacl_graph_format='turtle')
conforms1, v_graph1, v_text1 = validate(vali_graph, shacl_graph=shapes_graph,
                                     data_graph_format='turtle',
                                     shacl_graph_format='turtle',
                                     inference='none')
time_end1=time.time()


time_start2 =time.time()
v_graph2, same_list = noiseless_fused_graph(data_graph_0, shacl_graph=shapes_graph,data_graph_format='turtle',shacl_graph_format='turtle',merge_Type=True)
conforms2, g2, v_text2 = validate(v_graph2, shacl_graph=shapes_graph,
                                     data_graph_format='turtle',
                                     shacl_graph_format='turtle',
                                     inference='none')
time_end2=time.time()

time_start3 =time.time()
v_graph3, same_list2 = noiseless_fused_graph(data_graph_0, shacl_graph=shapes_graph,data_graph_format='turtle',shacl_graph_format='turtle',merge_Type=False)
conforms3, g3, v_text3 = validate(v_graph3, shacl_graph=shapes_graph,
                                     data_graph_format='turtle',
                                     shacl_graph_format='turtle',
                                     inference='none')
time_end3=time.time()

print('Runtime for example without errors: ', (time_end1-time_start1)*1000, 'ms [Fused Graph]')

print('Runtime for example without errors: ', (time_end2-time_start2)*1000, 'ms [Noiseless Fused Graph by removing nodes]')

print('Runtime for example without errors: ', (time_end3-time_start3)*1000, 'ms [Noiseless Fused Graph by adding nodes]')


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
print(v_text)
print(v_text1)
print(v_text2)
print(v_text3)





time_start4 =time.time()    
conforms4, v_graph4, v_text4 = validate(data_graph_1, shacl_graph=shapes_graph,
                                     data_graph_format='turtle',
                                     shacl_graph_format='turtle',
                                     inference='both')  
time_end4 =time.time() 
print('Runtime for example with errors: ', (time_end4-time_start4)*1000, 'ms [Naive method]')



time_start5 =time.time()
vali_graph5, same_g5 = fused_graph(data_graph_1, shacl_graph=shapes_graph,data_graph_format='turtle',shacl_graph_format='turtle')
conforms5, g5, v_text5 = validate(vali_graph5, shacl_graph=shapes_graph,
                                     data_graph_format='turtle',
                                     shacl_graph_format='turtle',
                                     inference='none')
time_end5=time.time()


time_start6 =time.time()
v_graph6, same_list6 = noiseless_fused_graph(data_graph_1, shacl_graph=shapes_graph,data_graph_format='turtle',shacl_graph_format='turtle',merge_Type=True)
conforms6, g6, v_text6 = validate(v_graph6, shacl_graph=shapes_graph,
                                     data_graph_format='turtle',
                                     shacl_graph_format='turtle',
                                     inference='none')
time_end6=time.time()

time_start7 =time.time()
v_graph7, same_list7 = noiseless_fused_graph(data_graph_1, shacl_graph=shapes_graph,data_graph_format='turtle',shacl_graph_format='turtle',merge_Type=False)
conforms7, g7, v_text7 = validate(v_graph7, shacl_graph=shapes_graph,
                                     data_graph_format='turtle',
                                     shacl_graph_format='turtle',
                                     inference='none')
time_end7=time.time()

print('Runtime for example with errors: ', (time_end5-time_start5)*1000, 'ms [Fused Graph]')

print('Runtime for example with errors: ', (time_end6-time_start6)*1000, 'ms [Noiseless Fused Graph by removing nodes]')

print('Runtime for example with errors: ', (time_end7-time_start7)*1000, 'ms [Noiseless Fused Graph by adding nodes]')


print("===================Fused Graph=====================")
print(vali_graph5.serialize(format="turtle"))
print("======================End==========================\n")

print("===============Noiseless Fused Graph=================")
print(v_graph6.serialize(format="turtle"))
print("=======================End===========================\n")


print("===============Noiseless Fused Graph 2=================")
print(v_graph7.serialize(format="turtle"))
print("=======================End===========================\n")


print("=======================Reports===========================\n")
print(v_text4)
print(v_text5)
print(v_text6)
print(v_text7)