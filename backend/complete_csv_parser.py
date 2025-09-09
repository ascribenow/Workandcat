#!/usr/bin/env python3
"""
Complete CSV Parser for Canonical Taxonomy
Downloads and parses the complete enriched CSV file
"""

import requests
import csv
import json
from collections import defaultdict
from io import StringIO

def download_and_parse_complete_csv():
    """Download the complete CSV and build taxonomy"""
    
    # Download CSV from the URL
    csv_url = "https://customer-assets.emergentagent.com/job_learn-compounded/artifacts/ouidzpsi_CSVCanonical_Taxonomy_Enriched_Reorganized.csv"
    
    try:
        response = requests.get(csv_url)
        response.raise_for_status()
        csv_content = response.text
        
        print(f"📥 Downloaded CSV: {len(csv_content)} characters")
        
        # Parse CSV
        csv_reader = csv.DictReader(StringIO(csv_content))
        
        # Build taxonomy structure
        taxonomy = defaultdict(lambda: defaultdict(lambda: {'description': '', 'types': {}}))
        
        row_count = 0
        for row in csv_reader:
            row_count += 1
            category = row['Category'].strip()
            subcategory = row['Subcategory'].strip()
            subcategory_desc = row['Subcategory Description'].strip()
            question_type = row['Type of questions'].strip()
            type_desc = row['Type of Question Description'].strip()
            
            # Set subcategory description if not already set
            if not taxonomy[category][subcategory]['description']:
                taxonomy[category][subcategory]['description'] = subcategory_desc
                
            # Add question type and its description
            taxonomy[category][subcategory]['types'][question_type] = type_desc
        
        print(f"📊 Processed {row_count} rows")
        
        # Convert to regular dict
        canonical_taxonomy = {}
        for category, subcategories in taxonomy.items():
            canonical_taxonomy[category] = {}
            for subcategory, data in subcategories.items():
                canonical_taxonomy[category][subcategory] = dict(data)
        
        # Print statistics
        total_categories = len(canonical_taxonomy)
        total_subcategories = sum(len(subs) for subs in canonical_taxonomy.values())
        total_types = sum(
            len(data['types']) 
            for category_data in canonical_taxonomy.values() 
            for subcategory, data in category_data.items()
        )
        
        print(f"✅ Built complete taxonomy:")
        print(f"   Categories: {total_categories}")
        print(f"   Subcategories: {total_subcategories}")
        print(f"   Question Types: {total_types}")
        
        return canonical_taxonomy
        
    except Exception as e:
        print(f"❌ Error downloading/parsing CSV: {e}")
        return None

def generate_complete_taxonomy_file():
    """Generate the complete canonical taxonomy file"""
    
    taxonomy = download_and_parse_complete_csv()
    if not taxonomy:
        return False
    
    # Generate Python code
    code = "# SINGLE SOURCE OF TRUTH - COMPLETE CANONICAL TAXONOMY FROM ENRICHED CSV\n"
    code += "CANONICAL_TAXONOMY = " + json.dumps(taxonomy, indent=4, ensure_ascii=False) + "\n"
    
    # Write to file
    with open('/app/backend/canonical_taxonomy_data.py', 'w', encoding='utf-8') as f:
        f.write(code)
    
    print("✅ Complete canonical taxonomy file generated!")
    return True

if __name__ == "__main__":
    print("🔄 Downloading and parsing complete canonical taxonomy...")
    success = generate_complete_taxonomy_file()
    if success:
        print("🎉 Complete canonical taxonomy ready!")
    else:
        print("💥 Failed to generate complete taxonomy!")
        exit(1)