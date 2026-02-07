#!/usr/bin/env python3
"""
Green Climate Fund Job Scraper
Scrapes job listings from https://jobs.greenclimate.fund/ and generates an RSS feed
"""

import time
from datetime import datetime, timezone
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from xml.dom import minidom

def setup_driver():
    """Set up Chrome WebDriver with appropriate options"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def scrape_gcf_jobs():
    """Scrape job listings from Green Climate Fund"""
    url = "https://jobs.greenclimate.fund/en/sites/CX_1001/jobs"

    print(f"Starting scraper for: {url}")
    driver = setup_driver()
    jobs = []

    try:
        # Enable logging to capture network requests
        driver.get(url)
        print("Page loaded, waiting for JavaScript to render...")

        # Wait longer for JavaScript to fully load job listings
        wait = WebDriverWait(driver, 30)

        # Try to wait for the main content area to load
        print("Waiting for page content to load...")
        time.sleep(15)  # Give JavaScript time to make API calls and render

        # Try clicking on different job type tabs to load jobs
        try:
            print("Attempting to click 'Staffs' tab to load job listings...")
            staffs_button = driver.find_elements(By.XPATH, "//*[contains(text(), 'Staffs')]")
            if staffs_button:
                staffs_button[0].click()
                time.sleep(5)
                print("Clicked 'Staffs' tab")
        except Exception as e:
            print(f"Could not click Staffs tab: {str(e)}")

        # Scroll down to trigger lazy loading
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)

        # Get page source after JavaScript rendering
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')

        # Debug: Uncomment to save HTML for troubleshooting
        # with open('debug_page.html', 'w', encoding='utf-8') as f:
        #     f.write(page_source)
        # print("Page source saved to debug_page.html for examination")

        # Try multiple strategies to find actual job listings
        job_elements = []

        # Strategy 1: Look for job requisition links (more specific)
        job_links = soup.find_all('a', href=lambda x: x and (
            '/requisition' in str(x).lower() or
            '/job/' in str(x) or
            'requisitionid' in str(x).lower() or
            'jobdetails' in str(x).lower()
        ))
        if job_links:
            print(f"Found {len(job_links)} job requisition links")
            job_elements = job_links

        # Strategy 2: Look for job title elements with links
        if not job_elements:
            # Look for elements that have both a title-like element and a link
            for element in soup.find_all(['div', 'article', 'li']):
                title_elem = element.find(['h2', 'h3', 'h4'], class_=lambda x: x and 'title' in str(x).lower())
                link_elem = element.find('a', href=True)
                if title_elem and link_elem:
                    job_elements.append(element)
            print(f"Found {len(job_elements)} elements with titles and links")

        # Strategy 3: Look for any structured job containers
        if not job_elements:
            job_elements = soup.find_all(['div', 'article'], attrs={
                'data-automation-id': lambda x: x and 'job' in str(x).lower()
            })
            print(f"Found {len(job_elements)} job container elements")

        # Filter out navigation/menu links
        filtered_elements = []
        skip_keywords = ['sitemap', 'account', 'sign-in', 'profile', 'help', 'about']

        for element in job_elements:
            text = element.get_text(strip=True).lower()
            link = element.get('href', '') if element.name == 'a' else ''

            # Skip if it's likely a navigation link
            if any(keyword in text for keyword in skip_keywords):
                continue
            if any(keyword in link.lower() for keyword in ['sitemap', 'sign-in', 'profile']):
                continue

            filtered_elements.append(element)

        job_elements = filtered_elements
        print(f"Processing {len(job_elements)} potential job listings (after filtering)...")

        for element in job_elements[:50]:  # Limit to first 50
            try:
                # Extract job information
                job_data = {}

                # Get job link first
                if element.name == 'a' and element.get('href'):
                    href = element['href']
                    job_data['link'] = href if href.startswith('http') else f"https://jobs.greenclimate.fund{href}"
                else:
                    link_elem = element.find('a', href=True)
                    if link_elem:
                        href = link_elem['href']
                        job_data['link'] = href if href.startswith('http') else f"https://jobs.greenclimate.fund{href}"
                    else:
                        continue  # Skip if no link found

                # For Oracle HCM, job links are often just /job/XXXX
                # We need to get the title and other info from surrounding elements

                # Get job title
                if element.name == 'a':
                    # The link element itself might contain the title
                    job_data['title'] = element.get_text(strip=True)

                    # Look for parent or sibling elements with more info
                    parent = element.find_parent(['div', 'article', 'li'])
                    if parent:
                        # Try to find location, department in parent
                        for child in parent.find_all(['span', 'div', 'p']):
                            text = child.get_text(strip=True)
                            if any(loc in text for loc in ['Remote', 'Hybrid', 'Incheon', 'Korea', 'Republic of Korea']):
                                job_data['location'] = text
                else:
                    # Find title within element
                    title_elem = element.find(['h2', 'h3', 'h4', 'a', 'span'], class_=lambda x: x and 'title' in str(x).lower())
                    if not title_elem:
                        title_elem = element.find('a')

                    if title_elem:
                        job_data['title'] = title_elem.get_text(strip=True)
                    else:
                        job_data['title'] = element.get_text(strip=True)[:100]

                # If we still don't have a proper title, fetch it from the job detail page
                if not job_data.get('title') or len(job_data['title']) < 5 or job_data['title'].startswith('Position'):
                    try:
                        print(f"  Fetching details for job {job_data['link'].split('/')[-1]}...")
                        driver.get(job_data['link'])
                        time.sleep(3)  # Wait for job page to load

                        job_page_source = driver.page_source
                        job_soup = BeautifulSoup(job_page_source, 'html.parser')

                        # Try to find job title on detail page
                        title_elem = job_soup.find('h1')
                        if not title_elem:
                            title_elem = job_soup.find(['h2', 'h3'], class_=lambda x: x and 'title' in str(x).lower())

                        if title_elem:
                            job_data['title'] = title_elem.get_text(strip=True)

                        # Try to find location on detail page
                        location_elem = job_soup.find(string=lambda x: x and any(loc in str(x) for loc in ['Location:', 'Posting Location']))
                        if location_elem:
                            location_parent = location_elem.find_parent()
                            if location_parent:
                                location_text = location_parent.get_text(strip=True)
                                # Clean up the location text
                                location_text = location_text.replace('Location:', '').replace('Posting Location', '').strip()
                                if location_text:
                                    job_data['location'] = location_text

                        # Go back to main page
                        driver.get(url)
                        time.sleep(2)

                    except Exception as e:
                        print(f"  Could not fetch detail page: {str(e)}")
                        # Keep the default title
                        if not job_data.get('title'):
                            job_data['title'] = f"Position {job_data['link'].split('/')[-1]}"

                # Get location if not already set
                if 'location' not in job_data:
                    location_elem = element.find(['span', 'div', 'p'], class_=lambda x: x and 'location' in str(x).lower())
                    if not location_elem:
                        location_elem = element.find(string=lambda x: x and any(loc in str(x) for loc in ['Remote', 'Incheon', 'Korea', 'Hybrid']))
                    job_data['location'] = location_elem.get_text(strip=True) if location_elem else "Green Climate Fund"

                # Get department/category
                dept_elem = element.find(['span', 'div', 'p'], class_=lambda x: x and ('department' in str(x).lower() or 'category' in str(x).lower()))
                job_data['department'] = dept_elem.get_text(strip=True) if dept_elem else ""

                # Get posting date if available
                date_elem = element.find(['span', 'div', 'time'], class_=lambda x: x and 'date' in str(x).lower())
                job_data['pubDate'] = date_elem.get_text(strip=True) if date_elem else ""

                # Create description
                description_parts = [job_data['title']]
                if job_data['location'] != "Not specified":
                    description_parts.append(f"Location: {job_data['location']}")
                if job_data['department']:
                    description_parts.append(f"Department: {job_data['department']}")

                job_data['description'] = " | ".join(description_parts)

                if job_data['title'] and job_data['link']:
                    jobs.append(job_data)
                    print(f"  [OK] {job_data['title']}")

            except Exception as e:
                print(f"  [ERROR] Error processing job element: {str(e)}")
                continue

        print(f"\nSuccessfully scraped {len(jobs)} jobs")

    except Exception as e:
        print(f"Error during scraping: {str(e)}")

    finally:
        driver.quit()

    return jobs

def generate_rss_feed(jobs, output_file='gcf_jobs.xml'):
    """Generate RSS 2.0 feed from job listings"""

    # Register atom namespace with proper prefix
    ET.register_namespace('atom', 'http://www.w3.org/2005/Atom')

    # Create RSS root element (namespace will be added automatically)
    rss = ET.Element('rss', version='2.0')

    # Create channel element
    channel = ET.SubElement(rss, 'channel')

    # Add channel metadata
    title = ET.SubElement(channel, 'title')
    title.text = 'Green Climate Fund Jobs'

    link = ET.SubElement(channel, 'link')
    link.text = 'https://jobs.greenclimate.fund/en/sites/CX_1001/jobs'

    description = ET.SubElement(channel, 'description')
    description.text = 'Job listings from Green Climate Fund'

    language = ET.SubElement(channel, 'language')
    language.text = 'en-us'

    # Add atom:link for self-reference
    atom_link = ET.SubElement(channel, '{http://www.w3.org/2005/Atom}link')
    atom_link.set('href', 'https://cinfoposte.github.io/gcf-jobs/gcf_jobs.xml')
    atom_link.set('rel', 'self')
    atom_link.set('type', 'application/rss+xml')

    # Add lastBuildDate
    last_build = ET.SubElement(channel, 'lastBuildDate')
    last_build.text = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')

    # Add job items
    for job in jobs:
        item = ET.SubElement(channel, 'item')

        item_title = ET.SubElement(item, 'title')
        item_title.text = job.get('title', 'Untitled Position')

        item_link = ET.SubElement(item, 'link')
        item_link.text = job.get('link', '')

        item_description = ET.SubElement(item, 'description')
        item_description.text = job.get('description', '')

        # Add GUID
        guid = ET.SubElement(item, 'guid')
        guid.set('isPermaLink', 'true')
        guid.text = job.get('link', '')

        # Add pubDate if available
        if job.get('pubDate'):
            pub_date = ET.SubElement(item, 'pubDate')
            try:
                # Try to parse and format the date
                pub_date.text = job['pubDate']
            except:
                pub_date.text = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')

    # Create pretty-printed XML
    xml_string = ET.tostring(rss, encoding='unicode')

    # Fix namespace prefix issue: replace ns0: with atom:
    xml_string = xml_string.replace('xmlns:ns0=', 'xmlns:atom=')
    xml_string = xml_string.replace('<ns0:', '<atom:')
    xml_string = xml_string.replace('</ns0:', '</atom:')

    # Remove duplicate xmlns:atom if it exists
    import re
    xml_string = re.sub(r'xmlns:atom="[^"]*"\s+xmlns:atom="[^"]*"', 'xmlns:atom="http://www.w3.org/2005/Atom"', xml_string)

    dom = minidom.parseString(xml_string)
    pretty_xml = dom.toprettyxml(indent='  ')

    # Remove extra blank lines
    pretty_xml = '\n'.join([line for line in pretty_xml.split('\n') if line.strip()])

    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(pretty_xml)

    print(f"\n[SUCCESS] RSS feed generated: {output_file}")
    print(f"  Total jobs in feed: {len(jobs)}")

def main():
    """Main execution function"""
    print("=" * 60)
    print("Green Climate Fund Job Scraper")
    print("=" * 60)

    # Scrape jobs
    jobs = scrape_gcf_jobs()

    if jobs:
        # Generate RSS feed
        generate_rss_feed(jobs)
        print("\n[SUCCESS] Scraping completed successfully!")
    else:
        print("\n[ERROR] No jobs found. Please check the website structure.")

    print("=" * 60)

if __name__ == "__main__":
    main()
