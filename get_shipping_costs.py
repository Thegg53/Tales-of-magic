from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import sys

eu_countries = [
    "Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czech Republic",
    "Denmark", "Estonia", "Finland", "France", "Germany", "Greece", "Hungary",
    "Ireland", "Italy", "Latvia", "Lithuania", "Luxembourg", "Malta",
    "Netherlands", "Poland", "Portugal", "Romania", "Slovakia", "Slovenia",
    "Spain", "Sweden"
]

# Check for debug flag
debug_mode = "--debug" in sys.argv
if debug_mode:
    eu_countries = eu_countries[:2]  # Only first 2 countries
    print("DEBUG MODE: Testing with first 2 countries (Austria, Belgium)")
else:
    print(f"NORMAL MODE: Processing all {len(eu_countries)} countries")

print(f"Starting Selenium driver...")
driver = webdriver.Chrome()
driver.get("https://help.cardmarket.com/en/ShippingCosts")
print("Page loaded.")
wait = WebDriverWait(driver, 10)

# Dismiss cookies consent dialog if it appears
try:
    print("Attempting to dismiss cookies dialog...")
    cookies_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'ACCEPT ALL')]|//button[contains(text(), 'Accept')]|//button[contains(text(), 'ONLY REQUIRED')]")))
    cookies_button.click()
    print("Cookies dialog dismissed.")
    time.sleep(1)
except:
    print("No cookies dialog found or already dismissed.")

def select_country(widget_class, country_name):
    print(f"  Clicking {widget_class}...")
    widget = wait.until(EC.presence_of_element_located((By.CLASS_NAME, widget_class)))
    input_box = widget.find_element(By.TAG_NAME, "input")
    input_box.click()
    options_ul = widget.find_element(By.CLASS_NAME, "u-select__options")
    options = options_ul.find_elements(By.CLASS_NAME, "u-select__option")
    for option in options:
        if option.text.strip() == country_name:
            print(f"  Found and clicking: {country_name}")
            option.click()
            return
    raise Exception(f"Country '{country_name}' not found in dropdown.")

output_lines = []
processed = 0

for country in eu_countries:
    processed += 1
    print(f"\n[{processed}/{len(eu_countries)}] Processing {country}...")
    
    select_country("u-shipping-widget__from", country)
    select_country("u-shipping-widget__to", "Denmark")
    print(f"  Waiting for table to load...")
    time.sleep(2)
    
    try:
        rows = driver.find_elements(By.XPATH, "//table//tr[td]")
        print(f"  Found {len(rows)} table rows")
        
        found_weights = []
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) >= 3:
                cell_texts = [c.text.strip() for c in cells]
                
                # Look for weight values (20, 50, 100) in the row
                for i, cell in enumerate(cell_texts):
                    if cell in ["20", "50", "100"]:
                        weight = cell
                        # Pattern: [Shipping Method(0), Tracked(1), Max Value(2), Weight(3), Stamp(4), Price(5), AvgDays(6)]
                        # Get the price regardless of tracked status
                        if i + 2 < len(cell_texts):
                            price = cell_texts[i + 2]
                            
                            line = f"{country}\t{weight}g\t{price}"
                            print(f"    ✓ {weight}g: {price}")
                            output_lines.append(line)
                            found_weights.append(weight)
        
        if not found_weights:
            print(f"  ⚠ WARNING: No 20/50/100 weight rows found!")
            print(f"  First 3 rows from table:")
            for row in rows[:3]:
                cells = row.find_elements(By.TAG_NAME, "td")
                print(f"    {[c.text.strip() for c in cells]}")
    except Exception as e:
        print(f"  ✗ ERROR: {e}")

driver.quit()

# Parse the collected data and organize by country/weight
data = {}
for line in output_lines:
    parts = line.strip().split('\t')
    if len(parts) >= 3:
        country = parts[0]
        weight = parts[1]  # '20g', '50g', '100g'
        price = parts[2]   # '2,70 €'
        
        if country not in data:
            data[country] = {'20g': [], '50g': [], '100g': []}
        
        if weight in data[country]:
            data[country][weight].append(price)

# Build markdown table
print("\n✓ Generating markdown table...")
countries = sorted(data.keys())
table_lines = ['## Shipping', 'https://help.cardmarket.com/en/ShippingCosts  ', '| Weight   \t|  Max cards  \t|', '|---\t|---\t|', '| 20g\t|  4\t|', '| 50g\t|  17\t|', '| 100g\t|  40\t|', '', '### Cheapest Places (shipping to DK, prices in Euro)', '', '| Country | 20g | 50g | 100g |', '|---------|-----|-----|------|']

for country in countries:
    prices_20 = ' / '.join(data[country]['20g']) if data[country]['20g'] else '-'
    prices_50 = ' / '.join(data[country]['50g']) if data[country]['50g'] else '-'
    prices_100 = ' / '.join(data[country]['100g']) if data[country]['100g'] else '-'
    
    table_lines.append(f'| {country} | {prices_20} | {prices_50} | {prices_100} |')

# Read current singles-mkm.md and replace the shipping section
with open('singles-mkm.md', 'r') as f:
    content = f.read()

# Find the start of the shipping section and remove old table
import re
shipping_start = content.find('## Shipping')
if shipping_start != -1:
    # Remove everything from ## Shipping onwards
    content = content[:shipping_start].rstrip() + '\n\n'

# Append the new table
content += '\n'.join(table_lines) + '\n'

# Write back to singles-mkm.md
with open('singles-mkm.md', 'w') as f:
    f.write(content)

print("✓ Updated singles-mkm.md with shipping table")
print(f"\n✓ Driver closed.")

# Save to file
with open('shipping_data.txt', 'w') as f:
    f.write("Country\tWeight\tNon-Registered\tTracked\n")
    for line in output_lines:
        f.write(line + "\n")

print(f"\n✓ Saved {len(output_lines)} rows to shipping_data.txt")
print(f"\nFIRST FEW LINES:")
for line in output_lines[:6]:
    print(f"  {line}")

