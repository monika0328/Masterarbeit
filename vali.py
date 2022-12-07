from pyshacl import validate
from os import path

from fused_graph import fused_graph, noiseless_fused_graph
import time

shapes_file = '''
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix ub: <http://swat.cse.lehigh.edu/onto/univ-bench.owl#>.
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
ub:UniversityShape
    a sh:NodeShape ;
    sh:targetClass ub:University ;
    sh:property [
        sh:path ub:name ;
        sh:maxCount 1 ;
        sh:minCount 1 ; ;
    ] .
ub:DepartmentShape
    a sh:NodeShape ;
    sh:targetClass ub:Department ;
    sh:property [
        sh:path ub:name ;
        sh:maxCount 1 ;
        sh:minCount 1 ; 
    ] ;
    sh:property [
        sh:path ub:subOrganizationOf ;
        sh:maxCount 1 ;
        sh:minCount 1 ;
        sh:node ub:UniversityShape ;
    ] .    
ub:GraduateCourseShape
    a sh:NodeShape ;
    sh:targetClass ub:GraduateCourse ;
    sh:property [
        sh:path ub:name ;
        sh:maxCount 1 ;
        sh:minCount 1 ; 
    ] . 
ub:GraduateStudentShape
    a sh:NodeShape ;
    sh:targetClass ub:GraduateStudent ;
    sh:property [
        sh:path ub:name ;
        sh:maxCount 1 ;
        sh:minCount 1 ; 
    ];
    sh:property [
        sh:path ub:advisor ;
        sh:maxCount 1 ;
        sh:minCount 1 ; 
    ];
    sh:property [
        sh:path ub:emailAddress ;
        sh:minCount 1 ; 
    ];
    sh:property [
        sh:path ub:memberOf ;
        sh:minCount 1 ; 
        sh:node ub:DepartmentShape ;
    ];
    sh:property [
        sh:path ub:takesCourse ;
        sh:minCount 1 ;
        sh:maxCount 3 ; 
        sh:node ub:GraduateCourseShape ;
    ];
    sh:property [
        sh:path ub:telephone ;
        sh:minCount 1 ; 
    ];
    sh:property [
        sh:path ub:undergraduateDegreeFrom ;
        sh:minCount 1 ; 
        sh:node ub:UniversityShape ;
    ]. 
'''

shapes_file2 = '''
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix ub: <http://swat.cse.lehigh.edu/onto/univ-bench.owl#>.
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
ub:UniversityShape
    a sh:NodeShape ;
    sh:targetClass ub:University ;
    sh:property [
        sh:path ub:name ;
        sh:maxCount 1 ;
        sh:minCount 1 ; ;
    ] .
ub:DepartmentShape
    a sh:NodeShape ;
    sh:targetClass ub:Department ;
    sh:property [
        sh:path ub:name ;
        sh:maxCount 1 ;
        sh:minCount 1 ; 
    ] ;
    sh:property [
        sh:path ub:subOrganizationOf ;
        sh:maxCount 1 ;
        sh:minCount 1 ;
        sh:node ub:UniversityShape ;
    ] .    
'''

#"""
time_start =time.time() 
conforms, v_graph, v_text = validate('/Users/kejin/Developer/MA-IMP/example/data/raw/LUBM-univ1.nt', shacl_graph=shapes_file, inference='both',
                                     serialize_report_graph=False, data_graph_format='turtle', shacl_graph_format='turtle')
time_end=time.time() 
print('Runtime for LUBM:', (time_end-time_start), 's [Naive method]')


import logging

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, filename="logfile", filemode="a+",
                        format="%(asctime)-15s %(levelname)-8s %(message)s")
    logging.info(v_text)

time_start1 =time.time()
result_graph,list = fused_graph('/Users/kejin/Developer/MA-IMP/example/data/raw/LUBM-univ1.nt',data_graph_format='turtle', shacl_graph=shapes_file,shacl_graph_format='turtle')
conforms1, g1, v_text1 = validate(result_graph, shacl_graph=shapes_file, inference='none',
                                     serialize_report_graph=False, data_graph_format='turtle', shacl_graph_format='turtle')
time_end1=time.time()
print('Runtime for LUBM: ', (time_end1-time_start1), 's [Fused Graph]')


time_start2 =time.time()
v_graph, same_list = noiseless_fused_graph('/Users/kejin/Developer/MA-IMP/example/data/raw/LUBM-univ1.nt',data_graph_format='turtle', shacl_graph=shapes_file,shacl_graph_format='turtle')
conforms2, g2, v_text2 = validate(v_graph, shacl_graph=shapes_file, inference='none',
                                     serialize_report_graph=False, data_graph_format='turtle', shacl_graph_format='turtle')
time_end2=time.time()
print('Runtime for LUBM: ', (time_end2-time_start2), 's [Noiseless Fused Graph by removing nodes]')



time_start3 =time.time()
v_graph2, same_list2 = noiseless_fused_graph('/Users/kejin/Developer/MA-IMP/example/data/raw/LUBM-univ1.nt',data_graph_format='turtle', shacl_graph=shapes_file,shacl_graph_format='turtle',merge_Type=False)
conforms3, g3, v_text3 = validate(v_graph2, shacl_graph=shapes_file, inference='none',
                                     serialize_report_graph=False, data_graph_format='turtle', shacl_graph_format='turtle')
time_end3=time.time()
print('Runtime for LUBM: ', (time_end3-time_start3), 's [Noiseless Fused Graph by adding nodes]')

print('Original Graph Size: ', len(result_graph))
print('Size of Noiseless Fused Graph by removing nodes: ', len(v_graph))
print('Size of Noiseless Fused Graph by adding nodes: ', len(v_graph2))

#"""
