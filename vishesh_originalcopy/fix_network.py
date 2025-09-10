#!/usr/bin/env python3
"""
This script removes all vehicle class restrictions from the network file.
"""
import xml.etree.ElementTree as ET
import os

def clean_network_file(input_file, output_file):
    # Parse the input XML file
    print(f"Processing {input_file}...")
    tree = ET.parse(input_file)
    root = tree.getroot()
    
    # Remove all disallow attributes from type elements
    for elem in root.findall('.//type'):
        if 'disallow' in elem.attrib:
            print(f"Removing disallowed vehicle classes from {elem.get('id', 'unnamed')}")
            del elem.attrib['disallow']
    
    # Remove all disallow attributes from lane elements
    for elem in root.findall('.//lane'):
        if 'disallow' in elem.attrib:
            print(f"Removing disallowed vehicle classes from lane {elem.get('id', 'unnamed')}")
            del elem.attrib['disallow']
    
    # Save the cleaned network
    tree.write(output_file, encoding='UTF-8', xml_declaration=True)
    print(f"Cleaned network saved to {output_file}")

if __name__ == "__main__":
    input_file = "net.net.xml"
    output_file = "net_clean_final.net.xml"
    
    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} not found!")
        sys.exit(1)
        
    clean_network_file(input_file, output_file)
    print("Network cleaning complete. Please use net_clean_final.net.xml for your simulation.")
