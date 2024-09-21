import os
import json
import re
import yaml
from datetime import datetime
from pathlib import Path

import google.generativeai as genai

# Directory paths
content_dir = Path('../content/recipes/')

# Ensure the content directory exists
content_dir.mkdir(parents=True, exist_ok=True)

genai.configure(api_key=os.environ['GOOGLE_GENAI_APIKEY'])


def generate_title(name, category):
    clean_name = name.lower().replace("cocktail", "").replace("the", "").replace("punch", "").replace("'", "")
    long_name = f"the {clean_name} {category}"
    short_name = f"{clean_name}"

    return [long_name.title(), short_name.title()]
    
def identify_base_spirit(ingredients):
    base_spirits = {
        'Bourbon': ['bourbon'],
        'Whiskey': ['whiskey', 'whisky', 'jack daniels', 'johnnie walker', 'jim beam'],
        'Rye': ['rye'],
        'Gin': ['gin'],
        'Vodka': ['vodka'],
        'Rum': ['rum', 'rhum', 'cachaca'],
        'Tequila': ['tequila', 'mezcal'],
        'Brandy': ['brandy', 'cognac', 'armagnac'],
        'Scotch': ['scotch'],
        'Wine': ['rose', 'red wine', 'white wine', 'champagne', 'cabernet', 'merlot', 'sauvignon blanc', 'reisling']
        # Add more as needed
    }
    
    for spirit, aliases in base_spirits.items():
        for ingredient in ingredients:
            if any(alias in ingredient['item'].lower() for alias in aliases):
                return spirit.lower()
    return None

def identify_cocktail_family(ingredients, drink_name):
    # Define families with variations in ingredients
    families = {
        'margarita': [['lemon', 'lime', 'sweet and sour'], ['sugar', 'syrup', 'agave'], ['orange liqueur', 'triple sec', 'grand marnier', 'cointreau', 'orange juice']],
        'highball': [['lemon', 'lime', 'rum', 'vodka'], ['soda water', 'club soda', 'carbonated water', 'tonic', 'cola', 'ginger ale', 'ginger beer', 'dr pepper', 'beer']],
        'french75': [['champagne', 'sparkling wine'], ['lemon'], ['sugar', 'simple syrup']],
        'sour': [['lemon', 'lime'], ['sugar', 'syrup', 'grenadine', 'cordial', 'cranberry juice', 'pineapple juice', 'liqueur']],
        'ancestral': [['sugar', 'syrup'], ['bitters']],
        'negroni': [['campari', 'amaro'], ['vermouth']],
        'spirit-forward': [['vermouth', 'fortified wine', 'dubonnet']],
        'martini': [['dry vermouth',  'lillet']],
    }
    
    for family, ingredient_groups in families.items():
        # Check if all groups of ingredients are represented in some form
        if all(any(any(ingredient_variant in ingredient['item'].lower() for ingredient_variant in group) for ingredient in ingredients) for group in ingredient_groups):
            return family
        
        # Special case for Martini where the name might give it away
        if 'martini' in drink_name.lower():
            return "martini"
        
        if 'fizz' in drink_name.lower():
            return "fizz"
        
        if 'punch' in drink_name.lower():
            return "punch"
    
    return "other"  # If no family matches

def round_to_nearest_quarter(value):
    return round(round(value * 4) / 4, 2)

def clean_measure(measure):
    if measure:
        measure = measure.strip()

        # Check for units in the original measure
        contains_oz = 'oz' in measure
        contains_parts = 'parts' in measure
        contains_cl = measure.lower().endswith("cl")
        contains_ml = 'ml' in measure.lower()
        contains_shots = 'shot' in measure

        # Handle mixed fractions like "2 1/2"
        mixed_fraction_pattern = re.compile(r'(\d+)\s*(\d+/\d+)')
        match = mixed_fraction_pattern.match(measure)
        if match:
            whole_number = int(match.group(1))
            fraction = eval(match.group(2))  # Converts fraction like "1/2" to decimal
            result = whole_number + fraction

            # Return with appropriate unit based on the original input
            if contains_oz or contains_parts:
                return f"{result} oz"
            return str(result)

        # Replace fractions like "1/2" with decimals
        measure = measure.replace('1/4', '0.25').replace('1/2', '0.5').replace('3/4', '0.75')

        # Convert metric to oz if necessary
        if contains_cl:
            cl_value = float(re.search(r"[\d\.]+", measure).group())
            oz_value = round_to_nearest_quarter(cl_value * 0.33814)
            return f"{oz_value} oz"
        elif contains_ml:
            ml_value = float(re.search(r"[\d\.]+", measure).group())
            oz_value = round_to_nearest_quarter(ml_value * 0.033814)
            return f"{oz_value} oz"

        # Handle "parts" to "oz" conversion
        if contains_parts:
            measure = measure.replace('parts', 'oz')

        # Convert shots to oz (1 shot = 1.5 oz)
        if contains_shots:
            shot_count = float(re.search(r"[\d\.]+", measure).group())
            oz_value = shot_count * 1.5
            return f"{oz_value} oz"

        # Return result with "oz" if original measure had "oz"
        if contains_oz or contains_parts:
            return measure

        return measure.strip().title()

    return ""

def escape_quotes(text):
    return text.replace('"', '\\"').replace("'", "\\'") if text else text

def clean_path(text):
    text = text.replace("/", "_")
    text = text.replace("-", "_")
    text = text.replace(".", "")
    text = text.replace("'", "")
    text = text.replace(" ", "_").strip()
    text = text.replace("___", "_").strip()
    text = text.replace("__", "_").strip()

    return text.lower()

def create_hugo_content(drink, source, get_ai_content):
    drink_path = clean_path(drink['strDrink'])

    has_alcohol = drink["strAlcoholic"].lower() == "alcoholic"
    print(drink["strDrink"])

    ingredients = [
        {"measure": clean_measure(drink[f"strMeasure{i}"]), 
            "item": drink[f"strIngredient{i}"].title()} 
        for i in range(1, 16) if f"strIngredient{i}" in drink and drink[f"strIngredient{i}"]
    ]

    # Load the descriptions from the JSON file
    if not get_ai_content:
        data_file_path = '../data/descriptions.json'
        if os.path.exists(data_file_path):
            with open(data_file_path, 'r') as f:
                descriptions = json.load(f)
        else:
            descriptions = {}
            
        history = descriptions.get(drink_path, "")["description"]

        # Load the flavors from the JSON file
        data_file_path = '../data/flavor.json'
        if os.path.exists(data_file_path):
            with open(data_file_path, 'r') as f:
                flavor = json.load(f)
        else:
            flavor = {}
            
        flavor_description = flavor.get(drink_path, "")["description"]

        # Load the tips from the JSON file
        data_file_path = '../data/tips.json'
        if os.path.exists(data_file_path):
            with open(data_file_path, 'r') as f:
                tips = json.load(f)
        else:
            tips = {}
            
        bartender_tips = tips.get(drink_path, "")["description"]

        # Load the visuals from the JSON file
        data_file_path = '../data/visuals.json'
        if os.path.exists(data_file_path):
            with open(data_file_path, 'r') as f:
                visuals_data = json.load(f)
        else:
            visuals_data = {}
            
        visuals = ""
        if visuals_data.get(drink_path, "") != "":
            visuals = visuals_data.get(drink_path, "")["description"]

    else:
        ingredients_string = ", ".join(str(x["item"]) for x in ingredients)
        visuals = generate_visual_description(drink["strDrink"], ingredients_string)
        history = generate_content(drink["strDrink"], ingredients_string)
        [flavor_description, bartender_tips] = generate_flavor_content(drink["strDrink"], ingredients_string)


  

    category = clean_path(drink["strCategory"])
    if category == "coffee_tea": category = "cafe"
    elif category == "homemade_liqueur": category = "liqueur"
    elif category == "ordinary_drink": category = "cocktail"
    elif category == "ordinary_drink": category = "cocktail"
    elif category == "punch_party_drink": category = "punch"
    elif category == "soft_drink": category = "nonalcoholic"
    elif category == "non_alcoholic": category = "nonalcoholic"
    elif category == "other_unknown" and "sour" in history.lower() : category = "cocktail"
    elif category == "other_unknown" and "lassi" in history.lower() : category = "shake"
    elif category == "other_unknown" and "smoothie" in history.lower() : category = "shake"
    elif category == "other_unknown" and "cream" in history.lower() : category = "shake"
    elif category == "other_unknown" and "punch" in history.lower() : category = "punch"
    elif category == "other_unknown" and "shake" in history.lower() : category = "shake"
    elif category == "other_unknown" and not has_alcohol : category = "nonalcoholic"


    # get from gemini
    
    
    [drink_name, short_name] = generate_title(drink["strDrink"], category)

    frontmatter = {
        "title": drink_name,
        "fullname": drink_name,
        "shortname": short_name,
        "description": history.replace("\n", "").replace('"', ''),
        "flavor_description": flavor_description.replace("\n", "").replace('"', ''),
        "bartender_tips": bartender_tips.replace("\n", "").replace('"', ''),
        "ingredients": ingredients,
        "instructions": [{"item": instr.strip() + "."} for instr in escape_quotes(drink["strInstructions"]).replace("\n", "").split('.') if instr.strip()],
        "glass": drink["strGlass"],
        "category": category,
        "has_alcohol": has_alcohol,
        "base_spirit": identify_base_spirit(ingredients) or [],
        "family": identify_cocktail_family(ingredients, drink["strDrink"]) if not "strFamily" in drink else drink["strFamily"],
        "visual": visuals.replace("\n", "").replace('"', ''),
        "source": source
    }

    # Escape quotes in the instructions to handle any quoted text correctly, then split by newline and period
    instructions = escape_quotes(drink["strInstructions"]).split('\n')

    frontmatter["instructions"] = []  # Initialize or ensure this list exists in frontmatter

    for instr in instructions:
        # Split each line by periods to separate individual instructions that might be concatenated
        for sentence in instr.split('.'):
            # Clean up the instruction: remove newlines, strip whitespace
            i = sentence.replace("\n", "").strip()
            if i:  # Check if the instruction isn't empty after stripping
                frontmatter["instructions"].append({
                    "item": i + "."  # Add back the period for consistency, assuming each instruction should end with one
                })


    # Create the content file
    content_path = content_dir / f"{drink_path}/index.md"
    cover_path = content_dir / f"{drink_path}/images/"
    pins_path = content_dir / f"{drink_path}/pins/"

    content_path.parent.mkdir(parents=True, exist_ok=True)
    cover_path.mkdir(parents=True, exist_ok=True)
    pins_path.mkdir(parents=True, exist_ok=True)

    with open(content_path, 'w', encoding='utf-8') as f:
        f.write("---\n")
        for key, value in frontmatter.items():
            if isinstance(value, list):
                f.write(f"{key}:\n")
                for item in value:
                    f.write(f"  - item: \"{item['item']}\"\n")
                    if "measure" in item:
                        f.write(f"    measure: \"{item['measure']}\"\n")
            
            elif isinstance(value, bool):
                f.write(f"{key}: {str(value).lower()}\n")
            else:
                f.write(f"{key}: \"{value}\"\n")
        f.write("---\n\n")

def process_json_files(directory, source, get_ai_content):
    for file in os.listdir(directory):
        if file.endswith(".json"):
            with open(directory / file, 'r', encoding='utf-8') as json_file:
                data = json.load(json_file)
                if data and "drinks" in data and data["drinks"] is not None:
                    for drink in data["drinks"]:
                        create_hugo_content(drink, source, get_ai_content)



def generate_content(drink_name, ingredients):
        ''' Generate a blog post using Google Gemini 1.5'''
        model = genai.GenerativeModel('gemini-1.5-flash')

        try:
            desc_prompt = f'You are a seasoned mixologist who has historical knowledge of cocktails.  For this cocktail "{drink_name}", which is made from "{ingredients}", describe the cocktail family this drink is from, and its origin - for my cocktails webpage.  Limit to 60 words or less.'
            post_desc_resp = model.generate_content(desc_prompt)
            # print(post_desc_resp.text)

    
            return post_desc_resp.text

        except Exception as ex:
            print(ex)
            return ""


def generate_flavor_content(drink_name, ingredients):
        ''' Generate a blog post using Google Gemini 1.5'''
        model = genai.GenerativeModel('gemini-1.5-flash')

        try:
            desc_prompt = f'You are a seasoned mixologist who has deep knowledge of cocktails.  For this cocktail "{drink_name}", which is made using "{ingredients}", please describe its taste profile. Limit to 100 words or less'
            post_desc_resp = model.generate_content(desc_prompt)
            print("FLAVOR:", post_desc_resp.text)

            tips_prompt = f'You are a seasoned mixologist who has deep knowledge of cocktails.  For this cocktail "{drink_name}", which is made using "{ingredients}", please describe any helpful bartender tips when making it. Limit to 100 words or less'
            post_tips_resp = model.generate_content(tips_prompt)
            print("TIPS:", post_tips_resp.text)

    
            return post_desc_resp.text, post_tips_resp.text

        except Exception as ex:
            print(ex)
            return ["", ""]
        
def generate_visual_description(drink_name, ingredients):
        ''' Generate a blog post using Google Gemini 1.5'''
        model = genai.GenerativeModel('gemini-1.5-flash')

        try:
            desc_prompt = f'You are a seasoned mixologist who has deep knowledge of cocktails.  For this cocktail "{drink_name}", which is made using "{ingredients}", please generate an LLM prompt describing what it looks like.'
            post_desc_resp = model.generate_content(desc_prompt)
            print("APPEARANCE:", post_desc_resp.text)

    
            return post_desc_resp.text

        except Exception as ex:
            print(ex)
            return ""


def store_descriptions_in_data_file():
    base_path = '../content/recipes/'  # Path to the directory with drink recipes
    desc_file_path = '../data/descriptions.json'  # Path to save the JSON file
    flavor_file_path = '../data/flavor.json'  # Path to save the JSON file
    tips_file_path = '../data/tips.json'  # Path to save the JSON file
    visuals_file_path = '../data/visuals.json'  # Path to save the JSON file
    descriptions = {}
    flavors = {}
    tips = {}
    visuals = {}

    # Loop through each folder inside 'content/recipes/'
    for drink_folder in os.listdir(base_path):
        drink_path = os.path.join(base_path, drink_folder, 'index.md')
        
        # Ensure the index.md file exists
        if os.path.isfile(drink_path):
            with open(drink_path, 'r') as f:
                content = f.read()
                
                # Extract front matter (YAML between the "---" markers)
                if content.startswith('---'):
                    front_matter = content.split('---')[1].replace("\\'", "'")
                    metadata = yaml.safe_load(front_matter)
                    
                    # Get the description field and store it in the dictionary
                    if 'description' in metadata:
                        descriptions[drink_folder] = {
                            "description": metadata['description']
                        }

                    if 'flavor_description' in metadata:
                        flavors[drink_folder] = {
                            "description": metadata['flavor_description']
                        }

                    if 'bartender_tips' in metadata:
                        tips[drink_folder] = {
                            "description": metadata['bartender_tips']
                        }

                    if 'visual' in metadata:
                        visuals[drink_folder] = {
                            "description": metadata['visual']
                        }
    
    # Save the descriptions to seo.json
    with open(desc_file_path, 'w') as json_file:
        json.dump(descriptions, json_file, indent=4)

    with open(flavor_file_path, 'w') as json_file:
        json.dump(flavors, json_file, indent=4)

    with open(tips_file_path, 'w') as json_file:
        json.dump(tips, json_file, indent=4)

    with open(visuals_file_path, 'w') as json_file:
        json.dump(visuals, json_file, indent=4)




json_dir = Path('thecocktailsofmine/')
# json_dir = Path('thecocktaildb/')

if __name__ == "__main__":
    process_json_files(json_dir, "personal_collection", False)
    # store_descriptions_in_data_file()
    print("All JSON files processed and Hugo content files created.")
