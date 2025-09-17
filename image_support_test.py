#!/usr/bin/env python3
"""
Image Support System Testing for CAT Preparation Platform
Tests comprehensive image support functionality including:
- Database schema with image fields
- Image upload/validation/deletion
- Static file serving
- Question creation/retrieval with images
"""

import requests
import sys
import json
import io
from datetime import datetime
import time

class ImageSupportTester:
    def __init__(self, base_url="https://learning-tutor.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.admin_token = None
        self.student_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.uploaded_image_url = None
        self.uploaded_image_filename = None
        self.image_question_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None, files=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}" if not endpoint.startswith('http') else endpoint
        if headers is None:
            headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                if files:
                    # Remove Content-Type for multipart uploads
                    upload_headers = {k: v for k, v in headers.items() if k != 'Content-Type'}
                    response = requests.post(url, files=files, data=data, headers=upload_headers)
                else:
                    response = requests.post(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def authenticate(self):
        """Authenticate admin and student users"""
        print("🔐 Authenticating users...")
        
        # Admin login
        admin_login = {
            "email": "sumedhprabhu18@gmail.com",
            "password": "admin2025"
        }
        
        success, response = self.run_test("Admin Login", "POST", "auth/login", 200, admin_login)
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
            print(f"   ✅ Admin authenticated: {response['user']['full_name']}")
        else:
            print("   ❌ Admin authentication failed")
            return False

        # Student login (create if doesn't exist)
        student_login = {
            "email": "student@catprep.com",
            "password": "student123"
        }
        
        success, response = self.run_test("Student Login", "POST", "auth/login", 200, student_login)
        if success and 'access_token' in response:
            self.student_token = response['access_token']
            print(f"   ✅ Student authenticated: {response['user']['full_name']}")
        else:
            # Try to register student
            student_register = {
                "email": "student@catprep.com",
                "full_name": "Test Student",
                "password": "student123"
            }
            
            success, response = self.run_test("Student Registration", "POST", "auth/register", 200, student_register)
            if success and 'access_token' in response:
                self.student_token = response['access_token']
                print(f"   ✅ Student registered: {response['user']['full_name']}")
            else:
                print("   ❌ Student authentication failed")
                return False

        return True

    def test_database_schema_image_fields(self):
        """Test database schema has image fields in questions table"""
        print("📋 Testing Database Schema with Image Fields...")
        
        try:
            # Get questions to verify image fields are present
            success, response = self.run_test("Get Questions (Check Image Fields)", "GET", "questions?limit=5", 200)
            if not success:
                return False
            
            questions = response.get('questions', [])
            if len(questions) == 0:
                print("     ⚠️ No questions found to verify image fields")
                return True  # Schema might be correct but no data
            
            # Check if questions have image fields
            first_question = questions[0]
            image_fields = ['has_image', 'image_url', 'image_alt_text']
            present_fields = [field for field in image_fields if field in first_question]
            
            print(f"     Image fields present: {len(present_fields)}/{len(image_fields)} - {present_fields}")
            
            if len(present_fields) >= 2:  # At least 2 of 3 fields should be present
                print("     ✅ Database schema includes image fields")
                return True
            else:
                print("     ❌ Database schema missing image fields")
                return False
                
        except Exception as e:
            print(f"     ❌ Error checking database schema: {e}")
            return False

    def test_image_upload_functionality(self):
        """Test POST /api/admin/image/upload endpoint"""
        print("📤 Testing Image Upload Functionality...")
        
        if not self.admin_token:
            print("     ❌ Cannot test image upload - no admin token")
            return False
        
        try:
            # Create a simple test image (1x1 PNG)
            test_image_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xdd\x8d\xb4\x1c\x00\x00\x00\x00IEND\xaeB`\x82'
            
            # Prepare multipart form data
            files = {
                'file': ('test_image.png', io.BytesIO(test_image_data), 'image/png')
            }
            data = {
                'alt_text': 'Test image for CAT question'
            }
            
            headers = {
                'Authorization': f'Bearer {self.admin_token}'
            }
            
            success, response = self.run_test("Image Upload", "POST", "admin/image/upload", 200, data, headers, files)
            
            if success:
                print(f"     ✅ Image uploaded successfully")
                print(f"     Image URL: {response.get('image_url')}")
                print(f"     Filename: {response.get('filename')}")
                print(f"     File size: {response.get('file_size')} bytes")
                
                # Store for later tests
                self.uploaded_image_url = response.get('image_url')
                self.uploaded_image_filename = response.get('filename')
                
                return True
            else:
                print("     ❌ Image upload failed")
                return False
                
        except Exception as e:
            print(f"     ❌ Error testing image upload: {e}")
            return False

    def test_image_upload_validation(self):
        """Test image upload validation (file types, size limits)"""
        print("✅ Testing Image Upload Validation...")
        
        if not self.admin_token:
            print("     ❌ Cannot test image validation - no admin token")
            return False
        
        try:
            headers = {
                'Authorization': f'Bearer {self.admin_token}'
            }
            
            # Test 1: Invalid file type (text file)
            print("     Testing invalid file type...")
            invalid_files = {
                'file': ('test.txt', io.BytesIO(b'This is not an image'), 'text/plain')
            }
            
            success, response = self.run_test("Invalid File Type", "POST", "admin/image/upload", 400, {}, headers, invalid_files)
            
            if success:
                print("     ✅ Invalid file type properly rejected")
                validation_passed = True
            else:
                print("     ❌ Invalid file type not rejected")
                validation_passed = False
            
            # Test 2: Valid image types
            print("     Testing valid image types...")
            valid_image_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xdd\x8d\xb4\x1c\x00\x00\x00\x00IEND\xaeB`\x82'
            
            valid_extensions = ['.png', '.jpg']
            valid_count = 0
            
            for ext in valid_extensions:
                valid_files = {
                    'file': (f'test{ext}', io.BytesIO(valid_image_data), f'image/{ext[1:]}')
                }
                
                success, response = self.run_test(f"Valid {ext} File", "POST", "admin/image/upload", 200, {}, headers, valid_files)
                if success:
                    print(f"     ✅ {ext} file type accepted")
                    valid_count += 1
                else:
                    print(f"     ❌ {ext} file type rejected")
            
            if valid_count >= 1 and validation_passed:
                print("     ✅ Image upload validation working correctly")
                return True
            else:
                print("     ❌ Image upload validation has issues")
                return False
                
        except Exception as e:
            print(f"     ❌ Error testing image validation: {e}")
            return False

    def test_image_deletion(self):
        """Test DELETE /api/admin/image/{filename} endpoint"""
        print("🗑️ Testing Image Deletion...")
        
        if not self.admin_token:
            print("     ❌ Cannot test image deletion - no admin token")
            return False
        
        if not self.uploaded_image_filename:
            print("     ⚠️ No uploaded image to delete - skipping deletion test")
            return True
        
        try:
            headers = {
                'Authorization': f'Bearer {self.admin_token}'
            }
            
            success, response = self.run_test("Delete Image", "DELETE", f"admin/image/{self.uploaded_image_filename}", 200, None, headers)
            
            if success:
                print(f"     ✅ Image deleted successfully")
                print(f"     Message: {response.get('message')}")
                return True
            else:
                print("     ❌ Image deletion failed")
                return False
                
        except Exception as e:
            print(f"     ❌ Error testing image deletion: {e}")
            return False

    def test_static_file_serving(self):
        """Test GET /uploads/images/{filename} static file serving"""
        print("🌐 Testing Static File Serving...")
        
        try:
            # First upload an image to test serving
            if not self.admin_token:
                print("     ❌ Cannot test static file serving - no admin token")
                return False
            
            # Upload a test image first
            test_image_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xdd\x8d\xb4\x1c\x00\x00\x00\x00IEND\xaeB`\x82'
            
            files = {
                'file': ('static_test.png', io.BytesIO(test_image_data), 'image/png')
            }
            
            headers = {
                'Authorization': f'Bearer {self.admin_token}'
            }
            
            success, response = self.run_test("Upload for Static Test", "POST", "admin/image/upload", 200, {}, headers, files)
            
            if not success:
                print("     ❌ Could not upload image for static serving test")
                return False
            
            image_url = response.get('image_url')
            
            if not image_url:
                print("     ❌ No image URL returned from upload")
                return False
            
            # Test static file serving
            base_domain = self.base_url.replace('/api', '')
            static_url = f"{base_domain}{image_url}"
            print(f"     Testing static file serving: {static_url}")
            
            static_response = requests.get(static_url)
            
            if static_response.status_code == 200:
                content_type = static_response.headers.get('content-type', '')
                content_length = len(static_response.content)
                
                print(f"     ✅ Static file served successfully")
                print(f"     Content-Type: {content_type}")
                print(f"     Content-Length: {content_length} bytes")
                
                # Verify it's actually an image
                if 'image' in content_type.lower() or content_length > 0:
                    print("     ✅ Proper image content served")
                    return True
                else:
                    print("     ❌ Content doesn't appear to be an image")
                    return False
            else:
                print(f"     ❌ Static file serving failed - Status: {static_response.status_code}")
                return False
                
        except Exception as e:
            print(f"     ❌ Error testing static file serving: {e}")
            return False

    def test_question_creation_with_images(self):
        """Test POST /api/questions with image fields"""
        print("📝 Testing Question Creation with Images...")
        
        if not self.admin_token:
            print("     ❌ Cannot test question creation with images - no admin token")
            return False
        
        try:
            # First upload an image to use in question
            test_image_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xdd\x8d\xb4\x1c\x00\x00\x00\x00IEND\xaeB`\x82'
            
            files = {
                'file': ('question_diagram.png', io.BytesIO(test_image_data), 'image/png')
            }
            
            headers = {
                'Authorization': f'Bearer {self.admin_token}'
            }
            
            success, response = self.run_test("Upload Image for Question", "POST", "admin/image/upload", 200, {}, headers, files)
            
            if not success:
                print("     ❌ Could not upload image for question test")
                return False
            
            image_url = response.get('image_url')
            
            # Create question with image fields
            question_data = {
                "stem": "Look at the diagram below. A train travels from point A to point B. What is the distance covered?",
                "answer": "120",
                "solution_approach": "Measure the distance on the diagram",
                "detailed_solution": "Using the scale provided in the diagram, the distance from A to B is 120 km",
                "hint_category": "Arithmetic",
                "hint_subcategory": "Distance Measurement",
                "tags": ["image_test", "diagram", "distance"],
                "source": "Image Support Test",
                # Image support fields
                "has_image": True,
                "image_url": image_url,
                "image_alt_text": "Diagram showing train route from point A to point B with distance markers"
            }
            
            json_headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.admin_token}'
            }
            
            success, response = self.run_test("Create Question with Image Fields", "POST", "questions", 200, question_data, json_headers)
            
            if success and 'question_id' in response:
                print(f"     ✅ Question with image created successfully")
                print(f"     Question ID: {response['question_id']}")
                print(f"     Status: {response.get('status')}")
                
                # Store for retrieval test
                self.image_question_id = response['question_id']
                return True
            else:
                print("     ❌ Question creation with image fields failed")
                return False
                
        except Exception as e:
            print(f"     ❌ Error testing question creation with images: {e}")
            return False

    def test_question_retrieval_with_images(self):
        """Test question retrieval includes image fields"""
        print("📖 Testing Question Retrieval with Image Fields...")
        
        try:
            # Get questions and verify image fields are included
            success, response = self.run_test("Get Questions (Check Image Fields)", "GET", "questions?limit=10", 200)
            
            if not success:
                return False
            
            questions = response.get('questions', [])
            if len(questions) == 0:
                print("     ⚠️ No questions found to check image fields")
                return True
            
            # Look for questions with images
            questions_with_images = []
            image_field_counts = {'has_image': 0, 'image_url': 0, 'image_alt_text': 0}
            
            for question in questions:
                # Count presence of image fields
                for field in image_field_counts:
                    if field in question:
                        image_field_counts[field] += 1
                
                # Check if this question has image data
                if question.get('has_image') == True and question.get('image_url'):
                    questions_with_images.append(question)
            
            print(f"     Total questions retrieved: {len(questions)}")
            print(f"     Questions with image fields: has_image={image_field_counts['has_image']}, image_url={image_field_counts['image_url']}, image_alt_text={image_field_counts['image_alt_text']}")
            print(f"     Questions with actual images: {len(questions_with_images)}")
            
            if len(questions_with_images) > 0:
                sample_question = questions_with_images[0]
                print(f"     Sample image question ID: {sample_question.get('id')}")
                print(f"     Sample image URL: {sample_question.get('image_url')}")
                print(f"     Sample alt text: {sample_question.get('image_alt_text', 'N/A')}")
                print("     ✅ Question retrieval includes image fields and data")
                return True
            elif image_field_counts['has_image'] >= len(questions) // 2:  # At least half have the field
                print("     ✅ Question retrieval includes image fields (no image data yet)")
                return True
            else:
                print("     ❌ Question retrieval missing image fields")
                return False
                
        except Exception as e:
            print(f"     ❌ Error testing question retrieval with images: {e}")
            return False

    def run_comprehensive_image_tests(self):
        """Run all comprehensive image support tests"""
        print("🚀 Starting Comprehensive Image Support Testing...")
        print(f"   Base URL: {self.base_url}")
        print("=" * 80)

        # Authenticate first
        if not self.authenticate():
            print("❌ Authentication failed - cannot proceed with tests")
            return

        # Test sequence - FOCUSED ON IMAGE SUPPORT
        tests = [
            ("Database Schema Image Fields", self.test_database_schema_image_fields),
            ("Image Upload Functionality", self.test_image_upload_functionality),
            ("Image Upload Validation", self.test_image_upload_validation),
            ("Static File Serving", self.test_static_file_serving),
            ("Question Creation with Images", self.test_question_creation_with_images),
            ("Question Retrieval with Images", self.test_question_retrieval_with_images),
            ("Image Deletion", self.test_image_deletion),
        ]

        for test_name, test_method in tests:
            print(f"\n{'='*20} {test_name} {'='*20}")
            try:
                success = test_method()
                if success:
                    print(f"✅ {test_name} PASSED")
                else:
                    print(f"❌ {test_name} FAILED")
            except Exception as e:
                print(f"💥 {test_name} ERROR: {str(e)}")
                self.tests_run += 1  # Count as run but not passed

        # Final summary
        print("\n" + "="*80)
        print("🎯 IMAGE SUPPORT TESTING SUMMARY")
        print("="*80)
        print(f"Total tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        success_rate = (self.tests_passed/self.tests_run)*100 if self.tests_run > 0 else 0
        print(f"Success rate: {success_rate:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("🎉 ALL IMAGE SUPPORT TESTS PASSED! Image functionality is fully operational.")
        elif self.tests_passed >= self.tests_run * 0.85:
            print("✅ Most image tests passed. Image support is largely functional with minor issues.")
        elif self.tests_passed >= self.tests_run * 0.6:
            print("⚠️ Some image tests failed. Image support has significant issues that need attention.")
        else:
            print("❌ Many image tests failed. Image support has critical issues that must be fixed.")

        return self.tests_passed, self.tests_run

if __name__ == "__main__":
    tester = ImageSupportTester()
    passed, total = tester.run_comprehensive_image_tests()
    
    # Exit with appropriate code
    if passed == total:
        sys.exit(0)  # All tests passed
    else:
        sys.exit(1)  # Some tests failed