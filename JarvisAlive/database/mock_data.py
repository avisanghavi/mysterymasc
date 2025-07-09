#!/usr/bin/env python3
"""
Comprehensive Mock Data System for HeyJarvis

This module provides realistic B2B data generation for demos and testing,
including companies, contacts, and sophisticated query utilities.
"""

import uuid
import random
import threading
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, HttpUrl, validator
from functools import lru_cache
import time


class CompanyNews(BaseModel):
    """News item for a company"""
    date: datetime
    title: str
    summary: str
    news_type: str  # "funding", "product", "partnership", "expansion", "acquisition"
    
    @validator('news_type')
    def validate_news_type(cls, v):
        valid_types = ["funding", "product", "partnership", "expansion", "acquisition"]
        if v not in valid_types:
            raise ValueError(f"news_type must be one of {valid_types}")
        return v


class Company(BaseModel):
    """Company data model"""
    id: str  # Format: "comp_[uuid]"
    name: str
    website: HttpUrl
    industry: str  # One of: "SaaS", "FinTech", "E-commerce", "Healthcare", "Manufacturing"
    sub_industry: str  # e.g., "HR Tech", "Payment Processing"
    employee_count: int
    employee_range: str  # "1-10", "11-50", "51-200", "201-500", "501-1000", "1000+"
    location: str  # "City, State/Country"
    headquarters: str
    founded_year: int
    description: str  # 50-100 words
    recent_news: List[CompanyNews]  # 3-5 items
    pain_points: List[str]  # 3-5 industry-specific pain points
    technologies: List[str]  # Tech stack
    funding_stage: str  # "Seed", "Series A", "Series B", "Series C+", "Public"
    revenue_range: str  # "$0-1M", "$1-10M", "$10-50M", "$50-100M", "$100M+"
    growth_rate: str  # "0-20%", "20-50%", "50-100%", "100%+"
    
    @validator('id')
    def validate_id(cls, v):
        if not v.startswith('comp_'):
            raise ValueError("Company ID must start with 'comp_'")
        return v
    
    @validator('industry')
    def validate_industry(cls, v):
        valid_industries = ["SaaS", "FinTech", "E-commerce", "Healthcare", "Manufacturing"]
        if v not in valid_industries:
            raise ValueError(f"industry must be one of {valid_industries}")
        return v
    
    @validator('employee_range')
    def validate_employee_range(cls, v):
        valid_ranges = ["1-10", "11-50", "51-200", "201-500", "501-1000", "1000+"]
        if v not in valid_ranges:
            raise ValueError(f"employee_range must be one of {valid_ranges}")
        return v
    
    @validator('funding_stage')
    def validate_funding_stage(cls, v):
        valid_stages = ["Seed", "Series A", "Series B", "Series C+", "Public"]
        if v not in valid_stages:
            raise ValueError(f"funding_stage must be one of {valid_stages}")
        return v


class Contact(BaseModel):
    """Contact data model"""
    id: str  # Format: "cont_[uuid]"
    first_name: str
    last_name: str
    full_name: str
    title: str
    department: str  # "Engineering", "Sales", "Marketing", "Product", "Operations"
    seniority: str  # "C-Level", "VP", "Director", "Manager", "Individual Contributor"
    company_id: str
    company_name: str  # Denormalized for convenience
    email: str
    linkedin_url: HttpUrl
    phone: Optional[str]  # Format: "+1-555-555-5555"
    location: str
    years_in_role: float
    pain_points: List[str]  # Role-specific pain points
    priorities: List[str]  # Current priorities
    reports_to: Optional[str]  # Title of manager
    
    @validator('id')
    def validate_id(cls, v):
        if not v.startswith('cont_'):
            raise ValueError("Contact ID must start with 'cont_'")
        return v
    
    @validator('department')
    def validate_department(cls, v):
        valid_departments = ["Engineering", "Sales", "Marketing", "Product", "Operations"]
        if v not in valid_departments:
            raise ValueError(f"department must be one of {valid_departments}")
        return v
    
    @validator('seniority')
    def validate_seniority(cls, v):
        valid_seniorities = ["C-Level", "VP", "Director", "Manager", "Individual Contributor"]
        if v not in valid_seniorities:
            raise ValueError(f"seniority must be one of {valid_seniorities}")
        return v
    
    @validator('full_name')
    def validate_full_name(cls, v, values):
        if 'first_name' in values and 'last_name' in values:
            expected = f"{values['first_name']} {values['last_name']}"
            if v != expected:
                raise ValueError("full_name must match first_name + last_name")
        return v
    
    @validator('email')
    def validate_email(cls, v):
        if '@' not in v or '.' not in v:
            raise ValueError("Invalid email format")
        return v


class Lead(BaseModel):
    """Lead data model for qualified prospects"""
    contact: Contact
    company: Company
    score: int  # 1-100 qualification score
    fit_reasons: List[str]  # Why this is a good fit
    next_action: str  # Recommended next step


class MockDataGenerator:
    """Comprehensive mock data generation system"""
    
    def __init__(self):
        self._companies: List[Company] = []
        self._contacts: List[Contact] = []
        self._lock = threading.Lock()
        self._generated = False
        
        # Industry-specific data
        self._industry_data = {
            "SaaS": {
                "sub_industries": ["HR Tech", "Sales Tech", "Marketing Tech", "Dev Tools", "Security"],
                "pain_points": [
                    "Scaling customer onboarding process",
                    "Reducing churn in mid-market segment",
                    "Improving API performance under load",
                    "Building channel partner program",
                    "Implementing usage-based pricing",
                    "Accelerating enterprise sales cycles"
                ],
                "technologies": ["Python", "AWS", "PostgreSQL", "Redis", "Kubernetes", "React", "Node.js"]
            },
            "FinTech": {
                "sub_industries": ["Payment Processing", "Banking", "Insurance", "Investment", "Lending"],
                "pain_points": [
                    "Meeting regulatory compliance requirements",
                    "Preventing fraud and financial crimes",
                    "Scaling transaction processing",
                    "Building mobile-first experiences",
                    "Integrating with legacy banking systems",
                    "Ensuring data security and privacy"
                ],
                "technologies": ["Java", "PostgreSQL", "AWS", "Kafka", "Docker", "React", "Microservices"]
            },
            "E-commerce": {
                "sub_industries": ["Retail", "Marketplace", "B2B Commerce", "Fashion", "Electronics"],
                "pain_points": [
                    "Optimizing conversion rates",
                    "Managing inventory across channels",
                    "Personalizing customer experiences",
                    "Reducing cart abandonment",
                    "Scaling during peak seasons",
                    "Building loyalty programs"
                ],
                "technologies": ["Shopify", "AWS", "MongoDB", "Redis", "React", "Node.js", "Elasticsearch"]
            },
            "Healthcare": {
                "sub_industries": ["Health Tech", "Medical Devices", "Pharmaceuticals", "Telemedicine", "Healthcare Analytics"],
                "pain_points": [
                    "Ensuring HIPAA compliance",
                    "Integrating with EHR systems",
                    "Improving patient outcomes",
                    "Reducing administrative burden",
                    "Scaling telehealth capabilities",
                    "Managing clinical data"
                ],
                "technologies": ["Python", "AWS", "PostgreSQL", "HL7", "React", "Docker", "Kubernetes"]
            },
            "Manufacturing": {
                "sub_industries": ["Industrial IoT", "Supply Chain", "Automation", "Quality Control", "Logistics"],
                "pain_points": [
                    "Optimizing supply chain efficiency",
                    "Implementing predictive maintenance",
                    "Ensuring quality control",
                    "Reducing operational costs",
                    "Managing inventory levels",
                    "Improving worker safety"
                ],
                "technologies": ["Python", "AWS", "PostgreSQL", "IoT", "Edge Computing", "ML/AI", "ERP"]
            }
        }
        
        # Names for diversity
        self._first_names = [
            "Sarah", "Michael", "Jennifer", "David", "Lisa", "Robert", "Maria", "James",
            "Laura", "Christopher", "Michelle", "Daniel", "Jessica", "Matthew", "Amanda",
            "Joseph", "Angela", "Thomas", "Rachel", "Brian", "Emily", "Mark", "Nicole",
            "Kevin", "Stephanie", "Steven", "Elizabeth", "Anthony", "Amy", "Ryan",
            "Kimberly", "Jason", "Donna", "Jeffrey", "Carol", "Jacob", "Ruth", "Gary",
            "Sharon", "Harold", "Priya", "Raj", "Yuki", "Chen", "Ahmed", "Fatima",
            "Carlos", "Ana", "Luis", "Isabella"
        ]
        
        self._last_names = [
            "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
            "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
            "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
            "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson",
            "Walker", "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen",
            "Hill", "Flores", "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera",
            "Campbell", "Mitchell", "Carter", "Roberts", "Patel", "Singh", "Kumar",
            "Sharma", "Chen", "Wang", "Liu", "Yang", "Zhang", "Li", "Ahmed", "Ali"
        ]
        
        # Company names by industry
        self._company_names = {
            "SaaS": [
                "CloudSync Technologies", "DataFlow Solutions", "WorkStream Pro", "TechStack Labs",
                "ConnectHub", "ScaleUp Systems", "FlowState Technologies", "NextGen Software",
                "InnovateTech", "StreamlineAI", "OptimizeCore", "AgileWorks", "PulseTech",
                "VelocityApp", "CloudFirst Solutions", "DataBridge Systems", "WorkFlow Labs",
                "TechAdvance", "SmartSync", "RapidScale"
            ],
            "FinTech": [
                "SecurePay Solutions", "FinanceFlow", "PaymentBridge", "CryptoSecure",
                "LendingTree Pro", "WealthTech", "InsuranceAI", "BankingCore", "FinOptics",
                "TradeTech Solutions", "CreditFlow", "RiskAnalytics", "PayCore Systems",
                "FinanceFirst", "SecureTransact"
            ],
            "E-commerce": [
                "ShopConnect", "RetailFlow", "MarketPlace Pro", "CommerceHub", "SalesTech",
                "OrderFlow Systems", "RetailOptimize", "ShopStream", "MarketSync",
                "CommercePro", "SalesForce Commerce", "ShopTech Solutions", "RetailCore",
                "MarketFlow", "CommerceFirst"
            ],
            "Healthcare": [
                "HealthTech Solutions", "MedFlow Systems", "CareConnect", "HealthSync",
                "MedicalAI", "PatientFirst", "HealthCore", "MedTech Pro", "CareStream",
                "HealthOptimize", "MedSync Solutions", "PatientFlow", "HealthBridge",
                "MedCore Systems", "CareFirst"
            ],
            "Manufacturing": [
                "ManufactureTech", "IndustrialAI", "FactoryFlow", "ProductionCore",
                "ManufactureSync", "IndustrialOptimize", "FactoryTech", "ProductionPro",
                "ManufactureFirst", "IndustrialFlow", "FactorySync", "ProductionTech",
                "ManufactureCore", "IndustrialFirst", "FactoryFirst"
            ]
        }
        
        # Locations
        self._locations = [
            "San Francisco, CA", "New York, NY", "Austin, TX", "Boston, MA", "Seattle, WA",
            "Chicago, IL", "Los Angeles, CA", "Denver, CO", "Atlanta, GA", "Miami, FL",
            "London, UK", "Berlin, Germany", "Toronto, Canada", "Amsterdam, Netherlands",
            "Singapore", "Sydney, Australia", "Tel Aviv, Israel", "Stockholm, Sweden",
            "Dublin, Ireland", "Barcelona, Spain"
        ]
        
    def generate_data(self) -> None:
        """Generate all mock data"""
        with self._lock:
            if self._generated:
                return
            
            start_time = time.time()
            
            # Generate companies first
            self._companies = self._generate_companies()
            
            # Generate contacts for those companies
            self._contacts = self._generate_contacts()
            
            self._generated = True
            
            # Ensure generation is under 100ms
            generation_time = (time.time() - start_time) * 1000
            if generation_time > 100:
                print(f"Warning: Data generation took {generation_time:.1f}ms (target: <100ms)")
    
    def _generate_companies(self) -> List[Company]:
        """Generate 50 companies with proper distribution"""
        companies = []
        used_names = set()
        
        # Distribution: 20 SaaS, 10 FinTech, 10 E-commerce, 10 other
        industry_counts = {
            "SaaS": 20,
            "FinTech": 10,
            "E-commerce": 10,
            "Healthcare": 5,
            "Manufacturing": 5
        }
        
        for industry, count in industry_counts.items():
            for i in range(count):
                company = self._generate_company(industry, used_names)
                companies.append(company)
                used_names.add(company.name)
        
        return companies
    
    def _generate_company(self, industry: str, used_names: set = None) -> Company:
        """Generate a single company"""
        company_id = f"comp_{uuid.uuid4().hex[:8]}"
        
        # Select name and ensure uniqueness
        industry_names = self._company_names[industry]
        available_names = [name for name in industry_names if name not in (used_names or set())]
        
        if not available_names:
            # Fallback: generate unique name with suffix
            base_name = random.choice(industry_names)
            suffix = random.randint(1, 999)
            name = f"{base_name} {suffix}"
        else:
            name = random.choice(available_names)
        
        # Generate website from name
        website_name = name.lower().replace(" ", "").replace("-", "")
        website = f"https://{website_name}.com"
        
        # Industry-specific data
        industry_info = self._industry_data[industry]
        sub_industry = random.choice(industry_info["sub_industries"])
        
        # Employee count and range
        employee_count = self._generate_employee_count()
        employee_range = self._get_employee_range(employee_count)
        
        # Location
        location = random.choice(self._locations)
        headquarters = location
        
        # Founded year
        founded_year = random.randint(2010, 2022)
        
        # Description
        description = self._generate_company_description(name, industry, sub_industry)
        
        # Recent news
        recent_news = self._generate_company_news(name, industry)
        
        # Pain points
        pain_points = random.sample(industry_info["pain_points"], random.randint(3, 5))
        
        # Technologies
        technologies = random.sample(industry_info["technologies"], random.randint(4, 6))
        
        # Funding stage
        funding_stage = random.choice(["Seed", "Series A", "Series B", "Series C+", "Public"])
        
        # Revenue range
        revenue_range = random.choice(["$0-1M", "$1-10M", "$10-50M", "$50-100M", "$100M+"])
        
        # Growth rate
        growth_rate = random.choice(["0-20%", "20-50%", "50-100%", "100%+"])
        
        return Company(
            id=company_id,
            name=name,
            website=website,
            industry=industry,
            sub_industry=sub_industry,
            employee_count=employee_count,
            employee_range=employee_range,
            location=location,
            headquarters=headquarters,
            founded_year=founded_year,
            description=description,
            recent_news=recent_news,
            pain_points=pain_points,
            technologies=technologies,
            funding_stage=funding_stage,
            revenue_range=revenue_range,
            growth_rate=growth_rate
        )
    
    def _generate_employee_count(self) -> int:
        """Generate realistic employee count"""
        # Weighted distribution
        ranges = [
            (1, 10, 0.15),      # 15% small
            (11, 50, 0.25),     # 25% startup
            (51, 200, 0.30),    # 30% growth
            (201, 500, 0.20),   # 20% mid-size
            (501, 1000, 0.07),  # 7% large
            (1001, 5000, 0.03)  # 3% enterprise
        ]
        
        rand = random.random()
        cumulative = 0
        
        for min_emp, max_emp, weight in ranges:
            cumulative += weight
            if rand <= cumulative:
                return random.randint(min_emp, max_emp)
        
        return random.randint(51, 200)  # Default
    
    def _get_employee_range(self, count: int) -> str:
        """Convert employee count to range string"""
        if count <= 10:
            return "1-10"
        elif count <= 50:
            return "11-50"
        elif count <= 200:
            return "51-200"
        elif count <= 500:
            return "201-500"
        elif count <= 1000:
            return "501-1000"
        else:
            return "1000+"
    
    def _generate_company_description(self, name: str, industry: str, sub_industry: str) -> str:
        """Generate company description"""
        templates = [
            f"{name} is a leading {industry} company specializing in {sub_industry.lower()} solutions. We help businesses streamline operations and drive growth through innovative technology platforms.",
            f"Founded as a {sub_industry.lower()} innovator, {name} delivers cutting-edge {industry.lower()} solutions to enterprises worldwide. Our platform enables organizations to optimize performance and accelerate digital transformation.",
            f"{name} provides enterprise-grade {sub_industry.lower()} solutions in the {industry.lower()} space. We empower companies to automate processes, reduce costs, and improve customer experiences through our advanced technology stack."
        ]
        
        return random.choice(templates)
    
    def _generate_company_news(self, name: str, industry: str) -> List[CompanyNews]:
        """Generate 3-5 recent news items"""
        news_items = []
        
        # Generate 3-5 news items within last 180 days
        for i in range(random.randint(3, 5)):
            days_ago = random.randint(1, 180)
            news_date = datetime.now() - timedelta(days=days_ago)
            
            news_type = random.choice(["funding", "product", "partnership", "expansion", "acquisition"])
            
            news_templates = {
                "funding": [
                    f"{name} Raises ${{amount}} Series {{series}}",
                    f"{name} Secures ${{amount}} in {{stage}} Funding",
                    f"{name} Closes ${{amount}} Funding Round"
                ],
                "product": [
                    f"{name} Launches New {industry} Platform",
                    f"{name} Announces Major Product Update",
                    f"{name} Introduces AI-Powered Features"
                ],
                "partnership": [
                    f"{name} Partners with {{partner}} for {{purpose}}",
                    f"{name} Announces Strategic Partnership",
                    f"{name} Expands Through Key Partnership"
                ],
                "expansion": [
                    f"{name} Expands to {{region}} Market",
                    f"{name} Opens New Office in {{location}}",
                    f"{name} Scales Operations Globally"
                ],
                "acquisition": [
                    f"{name} Acquires {{company}} to Expand {{capability}}",
                    f"{name} Announces Strategic Acquisition",
                    f"{name} Bolsters Platform Through Acquisition"
                ]
            }
            
            title_template = random.choice(news_templates[news_type])
            
            # Fill in template variables
            if news_type == "funding":
                amount = random.choice(["$5M", "$15M", "$25M", "$50M", "$100M"])
                series = random.choice(["A", "B", "C"])
                stage = random.choice(["Seed", "Series A", "Series B", "Growth"])
                title = title_template.format(amount=amount, series=series, stage=stage)
                summary = f"Led by top-tier investors to accelerate growth and expand market presence"
            elif news_type == "product":
                title = title_template
                summary = f"New features enhance user experience and platform capabilities"
            elif news_type == "partnership":
                partner = random.choice(["Microsoft", "Salesforce", "AWS", "Google Cloud"])
                purpose = random.choice(["integration", "go-to-market", "technology"])
                title = title_template.format(partner=partner, purpose=purpose)
                summary = f"Strategic collaboration to deliver enhanced value to customers"
            elif news_type == "expansion":
                region = random.choice(["European", "Asian", "Latin American"])
                location = random.choice(["London", "Berlin", "Tokyo", "Singapore"])
                title = title_template.format(region=region, location=location)
                summary = f"International expansion to serve growing customer base"
            else:  # acquisition
                company = random.choice(["TechCorp", "DataSystems", "CloudTech", "AILabs"])
                capability = random.choice(["analytics", "automation", "security", "integration"])
                title = title_template.format(company=company, capability=capability)
                summary = f"Acquisition strengthens platform and accelerates innovation"
            
            news_items.append(CompanyNews(
                date=news_date,
                title=title,
                summary=summary,
                news_type=news_type
            ))
        
        return sorted(news_items, key=lambda x: x.date, reverse=True)
    
    def _generate_contacts(self) -> List[Contact]:
        """Generate 100 contacts with proper distribution"""
        contacts = []
        
        # Target distribution
        seniority_targets = {
            "C-Level": 30,      # 30%
            "VP": 30,           # 30%
            "Director": 25,     # 25%
            "Manager": 15       # 15%
        }
        
        # Generate contacts for each seniority level
        for seniority, target_count in seniority_targets.items():
            for i in range(target_count):
                company = random.choice(self._companies)
                contact = self._generate_contact(company, seniority)
                contacts.append(contact)
        
        return contacts
    
    def _generate_contact(self, company: Company, seniority: str) -> Contact:
        """Generate a single contact"""
        contact_id = f"cont_{uuid.uuid4().hex[:8]}"
        
        # Generate name
        first_name = random.choice(self._first_names)
        last_name = random.choice(self._last_names)
        full_name = f"{first_name} {last_name}"
        
        # Generate title based on seniority
        title = self._generate_title(seniority)
        
        # Determine department
        department = self._determine_department(title)
        
        # Generate email
        email = self._generate_email(first_name, last_name, company.website)
        
        # Generate LinkedIn
        linkedin_url = f"https://linkedin.com/in/{first_name.lower()}-{last_name.lower()}-{random.randint(100, 999)}"
        
        # Generate phone (optional)
        phone = f"+1-{random.randint(555, 999)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}" if random.random() > 0.3 else None
        
        # Location (same as company)
        location = company.location
        
        # Years in role
        years_in_role = round(random.uniform(0.5, 8.0), 1)
        
        # Role-specific pain points
        pain_points = self._generate_role_pain_points(title, department)
        
        # Current priorities
        priorities = self._generate_priorities(title, department)
        
        # Reports to
        reports_to = self._generate_reports_to(seniority, department)
        
        return Contact(
            id=contact_id,
            first_name=first_name,
            last_name=last_name,
            full_name=full_name,
            title=title,
            department=department,
            seniority=seniority,
            company_id=company.id,
            company_name=company.name,
            email=email,
            linkedin_url=linkedin_url,
            phone=phone,
            location=location,
            years_in_role=years_in_role,
            pain_points=pain_points,
            priorities=priorities,
            reports_to=reports_to
        )
    
    def _generate_title(self, seniority: str) -> str:
        """Generate title based on seniority"""
        titles_by_seniority = {
            "C-Level": ["CEO", "CTO", "CFO", "CMO", "COO", "Chief Product Officer", "Chief Revenue Officer"],
            "VP": ["VP of Sales", "VP of Engineering", "VP of Marketing", "VP of Product", "VP of Operations"],
            "Director": ["Director of Sales", "Director of Engineering", "Director of Marketing", "Director of Product", "Director of Operations"],
            "Manager": ["Sales Manager", "Engineering Manager", "Marketing Manager", "Product Manager", "Operations Manager"]
        }
        
        return random.choice(titles_by_seniority[seniority])
    
    def _determine_department(self, title: str) -> str:
        """Determine department from title"""
        if any(word in title.lower() for word in ["sales", "revenue"]):
            return "Sales"
        elif any(word in title.lower() for word in ["engineering", "technology", "cto"]):
            return "Engineering"
        elif any(word in title.lower() for word in ["marketing", "cmo"]):
            return "Marketing"
        elif any(word in title.lower() for word in ["product"]):
            return "Product"
        else:
            return "Operations"
    
    def _generate_email(self, first_name: str, last_name: str, website: HttpUrl) -> str:
        """Generate email address"""
        domain = str(website).replace("https://", "").replace("http://", "")
        
        # Various email formats
        formats = [
            f"{first_name.lower()}.{last_name.lower()}@{domain}",
            f"{first_name.lower()[0]}.{last_name.lower()}@{domain}",
            f"{first_name.lower()}_{last_name.lower()}@{domain}",
            f"{first_name.lower()}{last_name.lower()}@{domain}"
        ]
        
        return random.choice(formats)
    
    def _generate_role_pain_points(self, title: str, department: str) -> List[str]:
        """Generate role-specific pain points"""
        pain_points_by_department = {
            "Sales": [
                "Qualifying leads more efficiently",
                "Shortening sales cycles",
                "Improving conversion rates",
                "Managing pipeline visibility",
                "Scaling outbound efforts"
            ],
            "Engineering": [
                "Reducing technical debt",
                "Improving deployment reliability",
                "Scaling system performance",
                "Optimizing development velocity",
                "Enhancing code quality"
            ],
            "Marketing": [
                "Attribution and ROI measurement",
                "Lead quality improvement",
                "Content scaling challenges",
                "Marketing automation complexity",
                "Brand awareness growth"
            ],
            "Product": [
                "Prioritizing feature development",
                "Understanding user needs",
                "Balancing technical debt",
                "Improving user onboarding",
                "Measuring product success"
            ],
            "Operations": [
                "Process optimization",
                "Cross-team coordination",
                "Resource allocation",
                "Performance monitoring",
                "Operational efficiency"
            ]
        }
        
        return random.sample(pain_points_by_department[department], random.randint(2, 4))
    
    def _generate_priorities(self, title: str, department: str) -> List[str]:
        """Generate current priorities"""
        priorities_by_department = {
            "Sales": [
                "Exceed quarterly targets",
                "Expand into new markets",
                "Improve team productivity",
                "Enhance customer relationships",
                "Optimize sales processes"
            ],
            "Engineering": [
                "Deliver key features on time",
                "Improve system reliability",
                "Enhance development processes",
                "Upgrade technology stack",
                "Optimize performance"
            ],
            "Marketing": [
                "Increase brand awareness",
                "Generate qualified leads",
                "Improve content strategy",
                "Optimize marketing spend",
                "Enhance customer experience"
            ],
            "Product": [
                "Launch new product features",
                "Improve user experience",
                "Increase user engagement",
                "Optimize product-market fit",
                "Enhance product analytics"
            ],
            "Operations": [
                "Streamline processes",
                "Improve operational efficiency",
                "Enhance team collaboration",
                "Optimize resource utilization",
                "Implement better tools"
            ]
        }
        
        return random.sample(priorities_by_department[department], random.randint(2, 3))
    
    def _generate_reports_to(self, seniority: str, department: str) -> Optional[str]:
        """Generate reports to title"""
        if seniority == "C-Level":
            return None
        elif seniority == "VP":
            return "CEO"
        elif seniority == "Director":
            return f"VP of {department}"
        else:  # Manager
            return f"Director of {department}"
    
    # Public API methods
    def get_companies(self) -> List[Company]:
        """Get all companies"""
        self.generate_data()
        return self._companies.copy()
    
    def get_contacts(self) -> List[Contact]:
        """Get all contacts"""
        self.generate_data()
        return self._contacts.copy()
    
    @lru_cache(maxsize=128)
    def get_companies_by_industry(self, industry: str) -> List[Company]:
        """Return all companies in specified industry"""
        self.generate_data()
        return [c for c in self._companies if c.industry == industry]
    
    @lru_cache(maxsize=128)
    def get_companies_by_size(self, min_employees: int, max_employees: int) -> List[Company]:
        """Return companies within employee range"""
        self.generate_data()
        return [c for c in self._companies if min_employees <= c.employee_count <= max_employees]
    
    def get_contacts_by_title(self, title_keywords: List[str]) -> List[Contact]:
        """Return contacts matching any title keyword (case-insensitive)"""
        self.generate_data()
        keywords_lower = [kw.lower() for kw in title_keywords]
        return [c for c in self._contacts if any(kw in c.title.lower() for kw in keywords_lower)]
    
    def get_contacts_by_seniority(self, seniority_levels: List[str]) -> List[Contact]:
        """Return contacts at specified seniority levels"""
        self.generate_data()
        return [c for c in self._contacts if c.seniority in seniority_levels]
    
    def get_qualified_leads(self, criteria: Dict[str, Any]) -> List[Lead]:
        """Return leads matching criteria"""
        self.generate_data()
        
        # Filter companies based on criteria
        companies = self._companies
        
        if "industries" in criteria:
            companies = [c for c in companies if c.industry in criteria["industries"]]
        
        if "company_sizes" in criteria:
            companies = [c for c in companies if c.employee_range in criteria["company_sizes"]]
        
        if "funding_stages" in criteria:
            companies = [c for c in companies if c.funding_stage in criteria["funding_stages"]]
        
        if "min_growth_rate" in criteria:
            # Simple growth rate filtering
            min_growth = criteria["min_growth_rate"]
            companies = [c for c in companies if c.growth_rate >= min_growth]
        
        # Find contacts at these companies
        company_ids = {c.id for c in companies}
        contacts = [c for c in self._contacts if c.company_id in company_ids]
        
        # Filter by titles if specified
        if "titles" in criteria:
            title_keywords = criteria["titles"]
            contacts = self.get_contacts_by_title(title_keywords)
            contacts = [c for c in contacts if c.company_id in company_ids]
        
        # Create leads
        leads = []
        for contact in contacts:
            company = next(c for c in companies if c.id == contact.company_id)
            
            # Generate qualification score
            score = self._calculate_lead_score(contact, company, criteria)
            
            # Generate fit reasons
            fit_reasons = self._generate_fit_reasons(contact, company, criteria)
            
            # Generate next action
            next_action = self._generate_next_action(contact, company, score)
            
            leads.append(Lead(
                contact=contact,
                company=company,
                score=score,
                fit_reasons=fit_reasons,
                next_action=next_action
            ))
        
        # Sort by score (highest first)
        return sorted(leads, key=lambda x: x.score, reverse=True)
    
    def _calculate_lead_score(self, contact: Contact, company: Company, criteria: Dict[str, Any]) -> int:
        """Calculate lead qualification score (1-100)"""
        score = 50  # Base score
        
        # Seniority boost
        seniority_boost = {
            "C-Level": 30,
            "VP": 25,
            "Director": 15,
            "Manager": 10
        }
        score += seniority_boost.get(contact.seniority, 0)
        
        # Company size boost
        if company.employee_count > 100:
            score += 10
        
        # Growth rate boost
        if "100%" in company.growth_rate:
            score += 15
        elif "50%" in company.growth_rate:
            score += 10
        
        # Funding stage boost
        if company.funding_stage in ["Series B", "Series C+", "Public"]:
            score += 10
        
        # Industry match
        if "industries" in criteria and company.industry in criteria["industries"]:
            score += 5
        
        return min(100, max(1, score))
    
    def _generate_fit_reasons(self, contact: Contact, company: Company, criteria: Dict[str, Any]) -> List[str]:
        """Generate reasons why this is a good fit"""
        reasons = []
        
        if contact.seniority in ["C-Level", "VP"]:
            reasons.append(f"Senior decision maker ({contact.title})")
        
        if company.employee_count > 200:
            reasons.append(f"Large company ({company.employee_count} employees)")
        
        if "100%" in company.growth_rate:
            reasons.append("High growth company")
        
        if company.funding_stage in ["Series B", "Series C+", "Public"]:
            reasons.append(f"Well-funded ({company.funding_stage})")
        
        if "industries" in criteria and company.industry in criteria["industries"]:
            reasons.append(f"Target industry ({company.industry})")
        
        return reasons
    
    def _generate_next_action(self, contact: Contact, company: Company, score: int) -> str:
        """Generate recommended next action"""
        if score >= 80:
            return "Schedule executive meeting"
        elif score >= 60:
            return "Send personalized outreach"
        elif score >= 40:
            return "Connect on LinkedIn"
        else:
            return "Research further"
    
    def get_company_by_id(self, company_id: str) -> Optional[Company]:
        """Return company by ID"""
        self.generate_data()
        return next((c for c in self._companies if c.id == company_id), None)
    
    def get_contact_by_id(self, contact_id: str) -> Optional[Contact]:
        """Return contact by ID"""
        self.generate_data()
        return next((c for c in self._contacts if c.id == contact_id), None)


# Global instance
_generator = MockDataGenerator()

# Convenience functions
def get_companies_by_industry(industry: str) -> List[Company]:
    """Return all companies in specified industry"""
    return _generator.get_companies_by_industry(industry)

def get_companies_by_size(min_employees: int, max_employees: int) -> List[Company]:
    """Return companies within employee range"""
    return _generator.get_companies_by_size(min_employees, max_employees)

def get_contacts_by_title(title_keywords: List[str]) -> List[Contact]:
    """Return contacts matching any title keyword (case-insensitive)"""
    return _generator.get_contacts_by_title(title_keywords)

def get_contacts_by_seniority(seniority_levels: List[str]) -> List[Contact]:
    """Return contacts at specified seniority levels"""
    return _generator.get_contacts_by_seniority(seniority_levels)

def get_qualified_leads(criteria: Dict[str, Any]) -> List[Lead]:
    """Return leads matching criteria"""
    return _generator.get_qualified_leads(criteria)

def get_company_by_id(company_id: str) -> Optional[Company]:
    """Return company by ID"""
    return _generator.get_company_by_id(company_id)

def get_contact_by_id(contact_id: str) -> Optional[Contact]:
    """Return contact by ID"""
    return _generator.get_contact_by_id(contact_id)

def get_all_companies() -> List[Company]:
    """Return all companies"""
    return _generator.get_companies()

def get_all_contacts() -> List[Contact]:
    """Return all contacts"""
    return _generator.get_contacts()

# Performance test function
def test_performance():
    """Test performance requirements"""
    import time
    
    # Test generation time
    start = time.time()
    _generator.generate_data()
    generation_time = (time.time() - start) * 1000
    
    print(f"Data generation time: {generation_time:.1f}ms (target: <100ms)")
    
    # Test query performance
    queries = [
        lambda: get_companies_by_industry("SaaS"),
        lambda: get_companies_by_size(50, 500),
        lambda: get_contacts_by_title(["VP", "Director"]),
        lambda: get_contacts_by_seniority(["C-Level", "VP"]),
        lambda: get_qualified_leads({"industries": ["SaaS", "FinTech"], "titles": ["VP", "Director"]})
    ]
    
    for i, query in enumerate(queries):
        start = time.time()
        result = query()
        query_time = (time.time() - start) * 1000
        print(f"Query {i+1} time: {query_time:.1f}ms (target: <10ms), results: {len(result)}")

if __name__ == "__main__":
    test_performance()