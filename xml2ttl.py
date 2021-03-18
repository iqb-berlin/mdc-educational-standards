from collections import namedtuple

from lxml import etree
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, RDF, SKOS, XSD, NamespaceManager
from pathlib import Path
import os, sys

ConceptScheme = namedtuple("ConceptScheme", ["conceptScheme", "concepts", "metadata"])
SchemeData = namedtuple("SchemeData", ["id", "label", "definition"])
LangString = namedtuple("LangString", ["value", "lang"])
MetaString = namedtuple("MetaString",["cat", "d", "value"])

core = Namespace('https://w3id.org/iqb/mdc-core/cs_')
lrmi = Namespace('http://purl.org/dcx/lrmi-terms/')
oeh_md = Namespace('http://w3id.org/openeduhub/learning-resource-terms/')

if len(sys.argv) > 1 and str(sys.argv[1]) == "help":
  exit("Please add an input xml file to the command line")

input_file =  sys.argv[1]

output_folder = Path("./data")
if not output_folder.exists():
    output_folder.mkdir()

def getValues(entry):
    if entry is not None:
        lang = entry.get("{http://www.w3.org/XML/1998/namespace}lang")
        value = entry.text
        return LangString(value, lang)
    else:
        return
def getMetaData(entry):
    if entry is not None:
        d = entry.get("def")
        cat = entry.get("cat")
        value = entry.text
        return MetaString(cat,d, value)

def parseXml():
    tree = etree.parse(input_file)
    md_lists = tree.xpath("//MDDef")

    conceptSchemes = []
    # get labels and values
    for item in md_lists:
        # get concept scheme id
        _id = str(item.get("id"))
        # get label
        label = getValues(item.find("Label"))
        definition = getValues(item.find("Description"))

        metadata = item.find("MDDefMetadata")
        md = []
        if(metadata is not None):
            for m in metadata:
                #get metadata
                # <MD cat="DOI:10.5159/IQB_MDR_Core_v1" def="1">8</MD>
                md.append(getMetaData(m))
        # get values
        # <Value id="1"><Label xml:lang="de">K1</Label><Description xml:lang="de">Mathematisch argumentieren</Description></Value>
        conceptScheme = SchemeData(_id, label, definition)

        values = item.findall("Value")
        concepts = []
        for value in values:
            _id = str(value.get("id"))
            label = getValues(value.find("Label"))
            definition = getValues(value.find("Description"))
            concepts.append(SchemeData(_id, label, definition))
        conceptSchemes.append(ConceptScheme(conceptScheme=conceptScheme, concepts=concepts,metadata=md))

    return conceptSchemes


def buildGraph(cs):
    conceptScheme = cs.conceptScheme
    concepts = cs.concepts
    metadata = cs.metadata

    g = Graph()
    base_url = URIRef("https://w3id.org/iqb/mdc-educational/cs_" + conceptScheme.id.zfill(3) + "/")
    metadataString = ""
    for md in metadata:
        if md.d == "1":
            #Bildungsniveau: https://w3id.org/iqb/mdc-core/cs_001/001
            metadataString += "Bildungsniveau: https://w3id.org/iqb/mdc-core/cs_" + md.d.zfill(3) + "/" + md.value.zfill(3) + "\n"
        elif md.d == "2":
            #Gültigkeitsbereich: https://w3id.org/iqb/mdc-core/cs_002/004
            metadataString += "Gültigkeitsbereich: https://w3id.org/iqb/mdc-core/cs_" + md.d.zfill(3) + "/" + md.value.zfill(3) + "\n"
        elif md.d == "3":
            #Fach: https://w3id.org/iqb/mdc-core/cs_003/004
            metadataString += "Fach: https://w3id.org/iqb/mdc-core/cs_" + md.d.zfill(3) + "/" + md.value.zfill(3) + "\n"
        else:
            continue

    g.add((base_url, RDF.type, SKOS.ConceptScheme))
    g.add((base_url, DCTERMS.creator, Literal("IQB - Institut zur Qualitätsentwicklung im Bildungswesen", lang="de")))
    g.add((base_url, DCTERMS.title, Literal(conceptScheme.label.value, lang=conceptScheme.label.lang )))
    if conceptScheme.definition:
        g.add((base_url, DCTERMS.description, Literal(conceptScheme.definition.value + "\n" + metadataString, lang=conceptScheme.definition.lang)))

        metadatastring2 = ""
        for md in metadata:
            # example: 001/001
            metadatastring2 = md.d.zfill(3) + "/" +  md.value.zfill(3)

            if(md.d == "1"):
                metadataString =  md.d.zfill(3) + "/" + md.value.zfill(3)
                g.add((base_url, oeh_md.educationalContext, URIRef(core + metadatastring2)))
                g.add((base_url, lrmi.educationalLevel, URIRef(core + metadatastring2)))
                g.add((base_url, DCTERMS.educationalLevel, URIRef(core + metadatastring2)))
            elif(md.d == "3"):
                metadataString =  md.d.zfill(3) + "/" + md.value.zfill(3)
                g.add((base_url, lrmi.teaches, URIRef(core + metadatastring2)))
            else:
                pass
            
            g.add((base_url, SKOS.relatedMatch, URIRef(core + metadatastring2)))
            
        
    for concept in concepts:
        concept_url = base_url + concept.id.zfill(3)
        g.add((concept_url, RDF.type, SKOS.Concept))
        g.add((concept_url, SKOS.prefLabel, Literal(concept.label.value, lang=concept.label.lang)))
        
        metadatastring2 = ""
        for md in metadata:
            # example: 001001
            metadatastring2 = md.d.zfill(3) + "/" +  md.value.zfill(3)

            if(md.d == "1"):
                metadataString =  md.d.zfill(3) + "/" + md.value.zfill(3)
                g.add((concept_url, oeh_md.educationalContext, URIRef(core + metadatastring2)))
                g.add((concept_url, lrmi.educationalLevel, URIRef(core + metadatastring2)))
            elif(md.d == "2"):
                metadataString =  md.d.zfill(3) + "/" + md.value.zfill(3)
                g.add((concept_url, SKOS.relatedMatch, URIRef(core + metadatastring2)))
            elif(md.d == "3"):
                metadataString =  md.d.zfill(3) + "/" + md.value.zfill(3)
                g.add((concept_url, lrmi.teaches, URIRef(core + metadatastring2)))
            else:
                pass

            g.add((concept_url, SKOS.relatedMatch, URIRef(core + metadatastring2)))
            
            # goal: core:001001
            

        if concept.definition:
            g.add((concept_url, SKOS.definition, Literal(concept.definition.value, lang=concept.definition.lang)))


            
        # add topConceptOf
        g.add((concept_url, SKOS.topConceptOf, base_url))
        g.add((base_url, SKOS.hasTopConcept, concept_url))
    
    
    
    g.bind("skos", SKOS)
    g.bind("dct", DCTERMS)
    g.bind("xsd", XSD)
    g.bind("core", core)
    g.bind("lrmi", lrmi)
    g.bind("oeh", oeh_md)

    outfile_path = output_folder / ("iqb_cs" + conceptScheme.id.zfill(3) + ".ttl")
    g.serialize(str(outfile_path), format="turtle", base=base_url, encoding="utf-8")


    

conceptSchemes = parseXml()

for item in conceptSchemes:
    buildGraph(item)
