"""
Example usage of Festival Film Scraper
This script demonstrates how to use the scraper programmatically
"""
import asyncio
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

async def example_scrape_aiff():
    """
    Example: Scrape AIFF 2024 festival films
    """
    from backend.services.festival_film_scraper import FestivalFilmScraper
    
    print("\n" + "="*70)
    print("  Example: Scraping AIFF 2024")
    print("="*70 + "\n")
    
    # Initialize scraper
    scraper = FestivalFilmScraper()
    
    # Festival URL
    festival_url = "https://aiff.runwayml.com/2024"
    
    print(f"🎬 Scraping: {festival_url}")
    print("⏳ This may take 10-30 seconds...\n")
    
    # Scrape films
    films = await scraper.scrape_festival_films(festival_url)
    
    # Display results
    print(f"\n✅ Found {len(films)} films:\n")
    
    for i, film in enumerate(films, 1):
        print(f"{i}. {film['title']}")
        if film.get('director'):
            print(f"   Director: {film['director']}")
        if film.get('category'):
            print(f"   Category: {film['category']}")
        print(f"   YouTube: {film['youtube_url']}")
        if film.get('duration'):
            print(f"   Duration: {film['duration']}")
        print()
    
    return films


async def example_api_call():
    """
    Example: Make API call to scrape festival films
    
    Note: This requires the API server to be running and authentication
    """
    import httpx
    
    print("\n" + "="*70)
    print("  Example: API Call to Scrape Festival Films")
    print("="*70 + "\n")
    
    # API endpoint
    api_url = "http://localhost:8000/festivals/scrape-films"
    
    # Request payload
    payload = {
        "festival_url": "https://aiff.runwayml.com/2024",
        "festival_name": "Runway AI Film Festival 2024"
    }
    
    # Headers (you need a valid admin token)
    headers = {
        "Authorization": "Bearer YOUR_ADMIN_TOKEN_HERE",
        "Content-Type": "application/json"
    }
    
    print("📡 Making API request...")
    print(f"URL: {api_url}")
    print(f"Payload: {payload}\n")
    
    # Make request
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                api_url,
                json=payload,
                headers=headers,
                timeout=60.0
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Success!")
                print(f"Films found: {result['films_found']}")
                print(f"Films imported: {result['films_imported']}")
                print(f"Films skipped: {result['films_skipped']}")
                
                if result.get('errors'):
                    print(f"\n⚠️ Errors: {len(result['errors'])}")
                    for error in result['errors']:
                        print(f"  - {error}")
                
                return result
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"Response: {response.text}")
                
    except httpx.ConnectError:
        print("❌ Error: Could not connect to API server")
        print("Make sure the server is running on localhost:8000")
    except Exception as e:
        print(f"❌ Error: {e}")


async def main():
    """Run examples"""
    print("\n" + "="*70)
    print("  Festival Film Scraper - Examples")
    print("="*70)
    
    # Check if Playwright is available
    try:
        from playwright.async_api import async_playwright
        print("\n✅ Playwright is installed and ready!\n")
    except ImportError:
        print("\n❌ Playwright is not installed!")
        print("Install with: pip install playwright && playwright install chromium\n")
        return
    
    # Example 1: Direct scraping
    print("\n" + "-"*70)
    print("Example 1: Direct Scraping (Programmatic)")
    print("-"*70)
    
    choice = input("\nRun this example? (y/N): ").strip().lower()
    if choice == 'y':
        await example_scrape_aiff()
    else:
        print("Skipped.\n")
    
    # Example 2: API call
    print("\n" + "-"*70)
    print("Example 2: API Call (Requires running server)")
    print("-"*70)
    
    choice = input("\nRun this example? (y/N): ").strip().lower()
    if choice == 'y':
        await example_api_call()
    else:
        print("Skipped.\n")
    
    print("\n" + "="*70)
    print("Examples complete!")
    print("See FESTIVAL_FILM_SCRAPER.md for more documentation")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
