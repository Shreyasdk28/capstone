#!/usr/bin/env python3
"""
This script cleans the network file by removing unsupported vehicle classes.
"""
import xml.etree.ElementTree as ET
import os

def clean_network(input_file, output_file):
    # Parse the input XML file
    tree = ET.parse(input_file)
    root = tree.getroot()
    
    # Define the vehicle classes we want to keep
    allowed_classes = {
        'passenger', 'private', 'taxi', 'bus', 'coach', 'delivery',
        'truck', 'trailer', 'emergency', 'motorcycle', 'bicycle',
        'authority', 'army', 'vip', 'hov', 'evehicle', 'tram',
        'rail_urban', 'rail', 'rail_electric', 'rail_fast', 'ship'
    }
    
    # Process all type and lane elements
    for elem in root.findall('.//type'):
        if 'disallow' in elem.attrib:
            # Clean up disallowed classes
            disallowed = elem.attrib['disallow'].split()
            cleaned = [vclass for vclass in disallowed if vclass in allowed_classes]
            if cleaned:
                elem.attrib['disallow'] = ' '.join(cleaned)
            else:
                del elem.attrib['disallow']
    
    # Save the cleaned network
    tree.write(output_file, encoding='UTF-8', xml_declaration=True)
    print(f"Cleaned network saved to {output_file}")

if __name__ == "__main__":
    input_file = "net.net.xml"
    output_file = "net_clean.net.xml"
    
    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} not found!")
        sys.exit(1)
        
    clean_network(input_file, output_file)
