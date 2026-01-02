"""
Simple validation test for festival film scraper code
Tests syntax and structure without requiring dependencies
"""
import ast
import sys

def test_file_syntax(filepath):
    """Test if a Python file has valid syntax"""
    try:
        with open(filepath, 'r') as f:
            code = f.read()
        
        ast.parse(code)
        print(f"✅ {filepath}: Valid Python syntax")
        return True
    except SyntaxError as e:
        print(f"❌ {filepath}: Syntax error at line {e.lineno}: {e.msg}")
        return False
    except Exception as e:
        print(f"❌ {filepath}: Error: {e}")
        return False

def check_required_methods(filepath, required_methods):
    """Check if a file contains required methods"""
    try:
        with open(filepath, 'r') as f:
            code = f.read()
        
        tree = ast.parse(code)
        found_methods = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                found_methods.append(node.name)
            elif isinstance(node, ast.AsyncFunctionDef):
                found_methods.append(node.name)
        
        missing = []
        for method in required_methods:
            if method not in found_methods:
                missing.append(method)
        
        if missing:
            print(f"❌ {filepath}: Missing methods: {', '.join(missing)}")
            return False
        else:
            print(f"✅ {filepath}: All required methods present ({len(required_methods)} found)")
            return True
            
    except Exception as e:
        print(f"❌ {filepath}: Error checking methods: {e}")
        return False

def check_required_classes(filepath, required_classes):
    """Check if a file contains required classes"""
    try:
        with open(filepath, 'r') as f:
            code = f.read()
        
        tree = ast.parse(code)
        found_classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                found_classes.append(node.name)
        
        missing = []
        for cls in required_classes:
            if cls not in found_classes:
                missing.append(cls)
        
        if missing:
            print(f"❌ {filepath}: Missing classes: {', '.join(missing)}")
            return False
        else:
            print(f"✅ {filepath}: All required classes present ({len(required_classes)} found)")
            return True
            
    except Exception as e:
        print(f"❌ {filepath}: Error checking classes: {e}")
        return False

def main():
    """Run validation tests"""
    print("\n" + "="*70)
    print("  Festival Film Scraper - Code Validation")
    print("="*70 + "\n")
    
    results = []
    
    # Test 1: Check festival_film_scraper.py
    print("Test 1: Festival Film Scraper Service")
    print("-" * 70)
    
    scraper_file = "backend/services/festival_film_scraper.py"
    results.append(test_file_syntax(scraper_file))
    results.append(check_required_classes(scraper_file, ["FestivalFilmScraper"]))
    results.append(check_required_methods(scraper_file, [
        "scrape_festival_films",
        "_scrape_aiff",
        "_scrape_generic",
        "_extract_youtube_url",
        "_extract_category",
        "_extract_duration"
    ]))
    
    # Test 2: Check festivals.py API endpoint
    print("\nTest 2: Festival API Endpoint")
    print("-" * 70)
    
    api_file = "backend/api/festivals.py"
    results.append(test_file_syntax(api_file))
    results.append(check_required_methods(api_file, ["scrape_festival_films"]))
    
    # Test 3: Check schemas.py
    print("\nTest 3: Request/Response Schemas")
    print("-" * 70)
    
    schemas_file = "backend/models/schemas.py"
    results.append(test_file_syntax(schemas_file))
    results.append(check_required_classes(schemas_file, [
        "FestivalFilmScrapeRequest",
        "FestivalFilmScrapeResponse",
        "ScrapedFilmData"
    ]))
    
    # Test 4: Check migrations
    print("\nTest 4: Database Migrations")
    print("-" * 70)
    
    migrations = [
        "backend/database/migrations/006_add_title_id_to_festival_submissions.sql",
        "backend/database/migrations/007_add_festival_fields_to_supabase_titles.sql"
    ]
    
    for migration in migrations:
        try:
            with open(migration, 'r') as f:
                content = f.read()
            
            # Basic SQL validation
            if "ALTER TABLE" in content or "CREATE" in content:
                print(f"✅ {migration}: Valid SQL migration file")
                results.append(True)
            else:
                print(f"❌ {migration}: No ALTER/CREATE statements found")
                results.append(False)
        except Exception as e:
            print(f"❌ {migration}: Error reading file: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "="*70)
    passed = sum(results)
    total = len(results)
    
    if all(results):
        print(f"✅ All tests passed! ({passed}/{total})")
        return 0
    else:
        print(f"❌ Some tests failed: {passed}/{total} passed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
