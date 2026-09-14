"""
MongoDB Seed Data Script

Populates the database with realistic sample data for development and testing.
Creates users, job postings, resumes, applications, and other entities.
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import random
from typing import List, Dict, Any

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.mongodb import connect_db, get_db
from app.db.collections import *
from app.utils.dates import utc_now


class DataSeeder:
    """Handles seeding of sample data."""
    
    def __init__(self):
        self.db = None
        self.created_users = []
        self.created_jobs = []
        self.created_resumes = []
    
    def connect(self):
        """Connect to MongoDB."""
        connect_db()
        self.db = get_db()
    
    def clear_existing_data(self):
        """Clear existing data (for development use)."""
        print("🧹 Clearing existing data...")
        
        collections_to_clear = [
            USERS_COLLECTION, USER_PROFILES_COLLECTION, RESUMES_COLLECTION,
            RESUME_ANALYSES_COLLECTION, JOBS_COLLECTION, APPLICATIONS_COLLECTION,
            INTERVIEWS_COLLECTION, ASSESSMENTS_COLLECTION, NOTIFICATIONS_COLLECTION,
            ANALYTICS_EVENTS_COLLECTION, ROADMAPS_COLLECTION, RECOMMENDATIONS_COLLECTION,
            CANDIDATES_COLLECTION, JOB_MATCHES_COLLECTION, SKILL_ASSESSMENTS_COLLECTION
        ]
        
        for collection_name in collections_to_clear:
            result = self.db[collection_name].delete_many({})
            print(f"  📄 {collection_name}: {result.deleted_count} documents deleted")
    
    def create_admin_user(self):
        """Create admin user."""
        print("\n👑 Creating admin user...")
        
        admin_user = {
            "email": settings.ADMIN_EMAIL,
            "hashed_password": get_password_hash(settings.ADMIN_PASSWORD),
            "role": "admin",
            "is_active": True,
            "is_verified": True,
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }
        
        # Check if admin already exists
        existing = self.db[USERS_COLLECTION].find_one({"email": settings.ADMIN_EMAIL})
        if existing:
            print(f"  ⚠️  Admin user already exists: {settings.ADMIN_EMAIL}")
            return existing["_id"]
        
        result = self.db[USERS_COLLECTION].insert_one(admin_user)
        admin_id = result.inserted_id
        
        # Create admin profile
        admin_profile = {
            "user_id": admin_id,
            "full_name": "System Administrator",
            "phone": "+1-555-0000",
            "location": "System",
            "bio": "Platform administrator with full system access",
            "avatar_url": None,
            "skills": ["System Administration", "Platform Management"],
            "education": [],
            "experience": [],
            "social_links": {},
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }
        
        self.db[USER_PROFILES_COLLECTION].insert_one(admin_profile)
        self.created_users.append(admin_id)
        
        print(f"  ✅ Admin user created: {settings.ADMIN_EMAIL}")
        return admin_id
    
    def create_sample_users(self, count: int = 20):
        """Create sample student and HR users."""
        print(f"\n👥 Creating {count} sample users...")
        
        # Student users data
        students = [
            {
                "email": "john.doe@student.edu", "name": "John Doe", 
                "skills": ["Python", "JavaScript", "React", "Node.js"],
                "bio": "Computer Science student passionate about full-stack development"
            },
            {
                "email": "jane.smith@student.edu", "name": "Jane Smith",
                "skills": ["Java", "Spring Boot", "MySQL", "AWS"],
                "bio": "Software engineering student with focus on backend systems"
            },
            {
                "email": "mike.johnson@student.edu", "name": "Mike Johnson",
                "skills": ["React", "TypeScript", "GraphQL", "PostgreSQL"],
                "bio": "Frontend developer with keen interest in modern web technologies"
            },
            {
                "email": "sarah.wilson@student.edu", "name": "Sarah Wilson",
                "skills": ["Python", "Data Science", "Machine Learning", "Pandas"],
                "bio": "Data science student working on ML and AI projects"
            },
            {
                "email": "alex.brown@student.edu", "name": "Alex Brown",
                "skills": ["Mobile Development", "Flutter", "Dart", "Firebase"],
                "bio": "Mobile app developer focusing on cross-platform solutions"
            }
        ]
        
        # HR users data
        hr_users = [
            {
                "email": "hr.manager@techcorp.com", "name": "Lisa Anderson", 
                "company": "TechCorp Solutions", "role": "HR Manager"
            },
            {
                "email": "recruiter@innovate.com", "name": "David Chen",
                "company": "Innovate Labs", "role": "Senior Recruiter"
            },
            {
                "email": "talent@startup.io", "name": "Emma Rodriguez",
                "company": "StartupIO", "role": "Talent Acquisition Specialist"
            }
        ]
        
        # Create student users
        for i, student in enumerate(students):
            user = {
                "email": student["email"],
                "hashed_password": get_password_hash("student123"),
                "role": "student",
                "is_active": True,
                "is_verified": True,
                "created_at": utc_now(),
                "updated_at": utc_now(),
            }
            
            result = self.db[USERS_COLLECTION].insert_one(user)
            user_id = result.inserted_id
            self.created_users.append(user_id)
            
            # Create profile
            profile = {
                "user_id": user_id,
                "full_name": student["name"],
                "phone": f"+1-555-{1000 + i:04d}",
                "location": random.choice(["New York, NY", "San Francisco, CA", "Austin, TX", "Seattle, WA"]),
                "bio": student["bio"],
                "avatar_url": None,
                "skills": student["skills"],
                "education": [
                    {
                        "degree": "Bachelor of Science",
                        "field": "Computer Science",
                        "institution": "State University",
                        "start_date": "2020-09-01",
                        "end_date": "2024-05-01",
                        "gpa": round(random.uniform(3.2, 4.0), 2)
                    }
                ],
                "experience": [
                    {
                        "title": "Software Development Intern",
                        "company": "Tech Startup",
                        "start_date": "2023-06-01",
                        "end_date": "2023-08-31",
                        "description": "Developed web applications using modern frameworks"
                    }
                ] if random.random() > 0.5 else [],
                "social_links": {
                    "linkedin": f"https://linkedin.com/in/{student['name'].lower().replace(' ', '')}"
                },
                "created_at": utc_now(),
                "updated_at": utc_now(),
            }
            
            self.db[USER_PROFILES_COLLECTION].insert_one(profile)
        
        # Create HR users
        for i, hr_user in enumerate(hr_users):
            user = {
                "email": hr_user["email"],
                "hashed_password": get_password_hash("hr123"),
                "role": "hr",
                "is_active": True,
                "is_verified": True,
                "created_at": utc_now(),
                "updated_at": utc_now(),
            }
            
            result = self.db[USERS_COLLECTION].insert_one(user)
            user_id = result.inserted_id
            self.created_users.append(user_id)
            
            # Create profile
            profile = {
                "user_id": user_id,
                "full_name": hr_user["name"],
                "phone": f"+1-555-{2000 + i:04d}",
                "location": "Corporate Office",
                "bio": f"{hr_user['role']} at {hr_user['company']}",
                "avatar_url": None,
                "skills": ["Recruitment", "HR Management", "Talent Acquisition"],
                "education": [
                    {
                        "degree": "Master of Business Administration",
                        "field": "Human Resources",
                        "institution": "Business School",
                        "start_date": "2015-09-01",
                        "end_date": "2017-05-01",
                        "gpa": 3.8
                    }
                ],
                "experience": [
                    {
                        "title": hr_user["role"],
                        "company": hr_user["company"],
                        "start_date": "2020-01-01",
                        "end_date": None,
                        "description": "Leading talent acquisition and HR operations"
                    }
                ],
                "social_links": {},
                "created_at": utc_now(),
                "updated_at": utc_now(),
            }
            
            self.db[USER_PROFILES_COLLECTION].insert_one(profile)
        
        print(f"  ✅ Created {len(students)} students and {len(hr_users)} HR users")
    
    def create_sample_jobs(self, count: int = 15):
        """Create sample job postings."""
        print(f"\n💼 Creating {count} sample job postings...")
        
        # Get HR users for job creation
        hr_users = list(self.db[USERS_COLLECTION].find({"role": "hr"}))
        
        job_templates = [
            {
                "title": "Software Engineer",
                "department": "Engineering",
                "type": "full_time",
                "experience_level": "entry",
                "skills": ["Python", "JavaScript", "Git", "SQL"],
                "description": "Join our engineering team to build scalable web applications"
            },
            {
                "title": "Frontend Developer", 
                "department": "Engineering",
                "type": "full_time",
                "experience_level": "mid",
                "skills": ["React", "TypeScript", "CSS", "JavaScript"],
                "description": "Create beautiful and responsive user interfaces"
            },
            {
                "title": "Backend Developer",
                "department": "Engineering", 
                "type": "full_time",
                "experience_level": "mid",
                "skills": ["Node.js", "Express", "MongoDB", "AWS"],
                "description": "Build robust APIs and backend systems"
            },
            {
                "title": "Data Scientist",
                "department": "Data",
                "type": "full_time", 
                "experience_level": "mid",
                "skills": ["Python", "Machine Learning", "SQL", "Statistics"],
                "description": "Extract insights from data to drive business decisions"
            },
            {
                "title": "DevOps Engineer",
                "department": "Infrastructure",
                "type": "full_time",
                "experience_level": "senior", 
                "skills": ["Docker", "Kubernetes", "AWS", "CI/CD"],
                "description": "Manage infrastructure and deployment pipelines"
            }
        ]
        
        companies = ["TechCorp Solutions", "Innovate Labs", "StartupIO", "Global Systems", "Digital Ventures"]
        locations = ["Remote", "New York, NY", "San Francisco, CA", "Austin, TX", "Seattle, WA"]
        
        for i in range(count):
            template = job_templates[i % len(job_templates)]
            hr_user = random.choice(hr_users)
            
            job = {
                "title": template["title"],
                "company": random.choice(companies),
                "department": template["department"], 
                "location": random.choice(locations),
                "job_type": template["type"],
                "experience_level": template["experience_level"],
                "salary_min": random.randint(50000, 80000),
                "salary_max": random.randint(90000, 150000),
                "description": template["description"],
                "requirements": template["skills"],
                "responsibilities": [
                    "Develop and maintain software applications",
                    "Collaborate with cross-functional teams",
                    "Write clean and efficient code",
                    "Participate in code reviews"
                ],
                "benefits": [
                    "Health insurance",
                    "401(k) matching", 
                    "Flexible work hours",
                    "Professional development budget"
                ],
                "status": "active",
                "application_deadline": utc_now() + timedelta(days=30),
                "posted_by": hr_user["_id"],
                "posted_at": utc_now() - timedelta(days=random.randint(1, 10)),
                "updated_at": utc_now(),
                "applicant_count": 0,
                "matching_config": {
                    "required_skills": template["skills"][:2],
                    "preferred_skills": template["skills"][2:],
                    "min_experience_years": 0 if template["experience_level"] == "entry" else 2,
                    "education_requirements": ["Bachelor's degree or equivalent experience"]
                }
            }
            
            result = self.db[JOBS_COLLECTION].insert_one(job)
            self.created_jobs.append(result.inserted_id)
        
        print(f"  ✅ Created {count} job postings")
    
    def create_sample_resumes(self):
        """Create sample resumes for student users."""
        print("\n📄 Creating sample resumes...")
        
        # Get student users
        student_users = list(self.db[USERS_COLLECTION].find({"role": "student"}))
        
        resume_count = 0
        for user in student_users[:3]:  # Create resumes for first 3 students
            profile = self.db[USER_PROFILES_COLLECTION].find_one({"user_id": user["_id"]})
            
            resume = {
                "user_id": user["_id"],
                "filename": f"{profile['full_name'].replace(' ', '_')}_Resume.pdf",
                "file_size": random.randint(50000, 200000),
                "file_url": f"https://example.com/resumes/{user['_id']}.pdf",
                "upload_date": utc_now() - timedelta(days=random.randint(1, 30)),
                "status": "processed",
                "extracted_text": f"Sample resume text for {profile['full_name']}...",
                "structured_data": {
                    "contact_info": {
                        "name": profile["full_name"],
                        "email": user["email"],
                        "phone": profile["phone"]
                    },
                    "skills": profile["skills"],
                    "education": profile["education"],
                    "experience": profile["experience"]
                }
            }
            
            result = self.db[RESUMES_COLLECTION].insert_one(resume)
            self.created_resumes.append(result.inserted_id)
            
            # Create resume analysis
            analysis = {
                "resume_id": result.inserted_id,
                "user_id": user["_id"],
                "health_score": random.randint(65, 95),
                "ats_score": random.randint(60, 90),
                "analysis_date": utc_now(),
                "strengths": [
                    "Strong technical skills",
                    "Clear formatting",
                    "Relevant experience"
                ],
                "weaknesses": [
                    "Could add more quantified achievements",
                    "Missing industry keywords"
                ],
                "suggestions": [
                    "Add more specific project details",
                    "Include relevant certifications"
                ],
                "keyword_analysis": {
                    "found_keywords": profile["skills"][:3],
                    "missing_keywords": ["Agile", "REST APIs", "Testing"],
                    "keyword_density": 0.15
                },
                "sections_analysis": {
                    "contact_info": {"score": 90, "feedback": "Complete contact information"},
                    "skills": {"score": 85, "feedback": "Good technical skills listed"},
                    "experience": {"score": 75, "feedback": "Could add more details"}
                }
            }
            
            self.db[RESUME_ANALYSES_COLLECTION].insert_one(analysis)
            resume_count += 1
        
        print(f"  ✅ Created {resume_count} resumes with analyses")
    
    def create_sample_applications(self):
        """Create sample job applications."""
        print("\n📝 Creating sample applications...")
        
        # Get some students and jobs
        students = list(self.db[USERS_COLLECTION].find({"role": "student"}).limit(3))
        jobs = list(self.db[JOBS_COLLECTION].find().limit(5))
        
        application_count = 0
        statuses = ["applied", "reviewing", "interview_scheduled", "rejected", "offered"]
        
        for student in students:
            # Each student applies to 2-3 jobs
            selected_jobs = random.sample(jobs, random.randint(2, 3))
            
            for job in selected_jobs:
                application = {
                    "job_id": job["_id"],
                    "user_id": student["_id"],
                    "resume_id": self.created_resumes[0] if self.created_resumes else None,
                    "cover_letter": "I am excited to apply for this position...",
                    "status": random.choice(statuses),
                    "applied_at": utc_now() - timedelta(days=random.randint(1, 15)),
                    "updated_at": utc_now(),
                    "timeline": [
                        {
                            "status": "applied",
                            "timestamp": utc_now() - timedelta(days=random.randint(1, 15)),
                            "note": "Application submitted"
                        }
                    ],
                    "hr_notes": "",
                    "match_score": round(random.uniform(0.6, 0.95), 2)
                }
                
                self.db[APPLICATIONS_COLLECTION].insert_one(application)
                
                # Update job applicant count
                self.db[JOBS_COLLECTION].update_one(
                    {"_id": job["_id"]},
                    {"$inc": {"applicant_count": 1}}
                )
                
                application_count += 1
        
        print(f"  ✅ Created {application_count} applications")
    
    def create_sample_notifications(self):
        """Create sample notifications."""
        print("\n🔔 Creating sample notifications...")
        
        users = list(self.db[USERS_COLLECTION].find().limit(5))
        notification_types = [
            "application_status_update",
            "new_job_match", 
            "interview_scheduled",
            "resume_analysis_complete",
            "system_announcement"
        ]
        
        notification_count = 0
        for user in users:
            # Create 2-3 notifications per user
            for _ in range(random.randint(2, 3)):
                notification = {
                    "user_id": user["_id"],
                    "type": random.choice(notification_types),
                    "title": "New Notification",
                    "message": "You have an update on your application status.",
                    "is_read": random.choice([True, False]),
                    "created_at": utc_now() - timedelta(days=random.randint(0, 7)),
                    "read_at": utc_now() - timedelta(days=random.randint(0, 3)) if random.choice([True, False]) else None,
                    "metadata": {
                        "job_id": str(random.choice(self.created_jobs)) if self.created_jobs else None
                    }
                }
                
                self.db[NOTIFICATIONS_COLLECTION].insert_one(notification)
                notification_count += 1
        
        print(f"  ✅ Created {notification_count} notifications")
    
    def create_analytics_events(self):
        """Create sample analytics events."""
        print("\n📊 Creating sample analytics events...")
        
        users = list(self.db[USERS_COLLECTION].find())
        event_types = [
            "user_login", "resume_upload", "job_view", "application_submit",
            "profile_update", "search_performed", "notification_read"
        ]
        
        event_count = 0
        # Create events for the last 30 days
        for day in range(30):
            date = utc_now() - timedelta(days=day)
            
            # Create 5-15 events per day
            for _ in range(random.randint(5, 15)):
                user = random.choice(users)
                
                event = {
                    "user_id": user["_id"],
                    "event_type": random.choice(event_types),
                    "timestamp": date,
                    "metadata": {
                        "user_agent": "Mozilla/5.0 (compatible)",
                        "ip_address": f"192.168.1.{random.randint(1, 254)}",
                        "session_id": f"sess_{random.randint(100000, 999999)}"
                    },
                    "properties": {}
                }
                
                self.db[ANALYTICS_EVENTS_COLLECTION].insert_one(event)
                event_count += 1
        
        print(f"  ✅ Created {event_count} analytics events")


def main():
    """Main seeding function."""
    print("🌱 Resume AI Platform - Database Seeding Script")
    print("=" * 60)
    
    seeder = DataSeeder()
    
    # Connect to database
    print("📡 Connecting to MongoDB...")
    try:
        seeder.connect()
        print("✅ Database connection established")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        sys.exit(1)
    
    # Ask for confirmation to clear existing data
    response = input("\n⚠️  This will clear existing data. Continue? (y/N): ").lower()
    if response != 'y':
        print("❌ Seeding cancelled")
        sys.exit(0)
    
    try:
        # Clear existing data
        seeder.clear_existing_data()
        
        # Create sample data
        seeder.create_admin_user()
        seeder.create_sample_users()
        seeder.create_sample_jobs()
        seeder.create_sample_resumes()
        seeder.create_sample_applications()
        seeder.create_sample_notifications()
        seeder.create_analytics_events()
        
        print("\n🎉 Database seeding completed successfully!")
        print("\nSample data created:")
        print(f"  👥 Users: {len(seeder.created_users)} (including admin)")
        print(f"  💼 Jobs: {len(seeder.created_jobs)}")
        print(f"  📄 Resumes: {len(seeder.created_resumes)}")
        
        print("\nTest accounts:")
        print(f"  🔑 Admin: {settings.ADMIN_EMAIL} / {settings.ADMIN_PASSWORD}")
        print("  👨‍🎓 Student: john.doe@student.edu / student123")
        print("  👩‍💼 HR: hr.manager@techcorp.com / hr123")
        
    except Exception as e:
        print(f"❌ Error during seeding: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()