import pytest
import asyncio
from datetime import datetime, timedelta
from typing import List
import time
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from departments.sales.agents.lead_scanner_implementation import (
    LeadScannerAgent, ScanCriteria, LeadScore, Lead
)
from database.mock_data import Company, Contact, CompanyNews


class TestLeadScanner:
    @pytest.fixture
    def scanner(self):
        """Create scanner instance for testing"""
        return LeadScannerAgent(mode="mock")
        
    @pytest.fixture
    def sample_criteria(self):
        """Standard test criteria"""
        return ScanCriteria(
            industries=["SaaS"],
            titles=["CTO", "VP Engineering"],
            company_sizes=["small"],
            min_score=70
        )
    
    @pytest.fixture
    def sample_company(self):
        """Create a sample company for testing"""
        return Company(
            id="comp_test123",
            name="TestTech Inc",
            website="https://testtech.com",
            industry="SaaS",
            sub_industry="HR Tech",
            employee_count=150,
            employee_range="51-200",
            location="San Francisco, CA",
            headquarters="San Francisco, CA",
            founded_year=2018,
            description="Test company for unit testing",
            recent_news=[
                CompanyNews(
                    date=datetime.now() - timedelta(days=15),
                    title="TestTech raises Series A",
                    summary="Raised $10M in Series A funding",
                    news_type="funding"
                )
            ],
            pain_points=["Scaling infrastructure", "Customer retention"],
            technologies=["Python", "React", "AWS"],
            funding_stage="Series A",
            revenue_range="$1M-$10M",
            growth_rate=150
        )
    
    @pytest.fixture
    def sample_contact(self):
        """Create a sample contact for testing"""
        return Contact(
            id="cont_test456",
            first_name="John",
            last_name="Doe",
            full_name="John Doe",
            title="Chief Technology Officer",
            department="Engineering",
            seniority="C-Level",
            company_id="comp_test123",
            company_name="TestTech Inc",
            email="john.doe@testtech.com",
            linkedin_url="https://linkedin.com/in/johndoe",
            phone="+1-555-0123",
            location="San Francisco, CA",
            years_in_role=2,
            pain_points=["Technical debt", "Hiring engineers"],
            priorities=["Scaling infrastructure", "Security"],
            reports_to=None
        )

    # ========== Unit Tests for Scoring Algorithm ==========
    
    def test_exact_industry_match_scores_30(self, scanner, sample_company):
        """Test that exact industry match gives 30 points"""
        criteria = ScanCriteria(industries=["SaaS"])
        score = scanner._calculate_industry_match(sample_company, criteria)
        assert score == 30, f"Expected 30 for exact match, got {score}"
    
    def test_related_industry_scores_20(self, scanner):
        """Test that related industries score appropriately"""
        # Test FinTech company with Financial Services criteria
        company = Company(
            id="comp_test",
            name="Test",
            website="https://test.com",
            industry="FinTech",
            sub_industry="Payments",
            employee_count=100,
            employee_range="51-200",
            location="New York, NY",
            headquarters="New York, NY",
            founded_year=2020,
            description="Test",
            recent_news=[],
            pain_points=[],
            technologies=[],
            funding_stage="Series A",
            revenue_range="$1M-$10M",
            growth_rate=100
        )
        
        criteria = ScanCriteria(industries=["Financial Services"])
        score = scanner._calculate_industry_match(company, criteria)
        assert score == 20, f"Expected 20 for related industry, got {score}"
    
    def test_title_variations_match_correctly(self, scanner):
        """Test CTO matches Chief Technology Officer"""
        contact1 = Contact(
            id="cont_1",
            first_name="Jane",
            last_name="Smith",
            full_name="Jane Smith",
            title="CTO",
            department="Engineering",
            seniority="C-Level",
            company_id="comp_1",
            company_name="Tech Co",
            email="jane@tech.com",
            linkedin_url="https://linkedin.com/in/jane",
            phone="+1-555-0001",
            location="NYC",
            years_in_role=3,
            pain_points=[],
            priorities=[],
            reports_to=None
        )
        
        contact2 = Contact(
            id="cont_2",
            first_name="Bob",
            last_name="Jones",
            full_name="Bob Jones",
            title="Chief Technology Officer",
            department="Engineering",
            seniority="C-Level",
            company_id="comp_2",
            company_name="Tech Co 2",
            email="bob@tech2.com",
            linkedin_url="https://linkedin.com/in/bob",
            phone="+1-555-0002",
            location="SF",
            years_in_role=2,
            pain_points=[],
            priorities=[],
            reports_to=None
        )
        
        criteria = ScanCriteria(titles=["CTO"])
        
        score1 = scanner._calculate_title_relevance(contact1, criteria)
        score2 = scanner._calculate_title_relevance(contact2, criteria)
        
        assert score1 == 30, f"Expected 30 for exact CTO match, got {score1}"
        assert score2 >= 20, f"Expected at least 20 for 'Chief Technology Officer', got {score2}"
    
    def test_company_size_exact_match_scores_20(self, scanner, sample_company):
        """Test exact size range match"""
        criteria = ScanCriteria(company_sizes=["small"])  # 51-200 employees
        score = scanner._calculate_company_size_fit(sample_company, criteria)
        assert score == 20, f"Expected 20 for exact size match, got {score}"
    
    def test_recent_news_scores_correctly(self, scanner, sample_company):
        """Test news recency scoring"""
        # Company has news from 15 days ago
        score = scanner._calculate_recent_activity(sample_company)
        # Should score 20 for news within 30 days
        assert score >= 20, f"Expected at least 20 for recent news, got {score}"
    
    def test_combined_score_calculation(self, scanner, sample_company, sample_contact):
        """Test that all scores combine correctly to 0-100"""
        criteria = ScanCriteria(
            industries=["SaaS"],
            titles=["CTO", "Chief Technology Officer"],
            company_sizes=["small"]
        )
        
        score = scanner.score_lead(sample_contact, sample_company, criteria)
        
        assert 0 <= score.total_score <= 100, f"Total score {score.total_score} not in range 0-100"
        assert score.industry_match + score.title_relevance + score.company_size_fit + score.recent_activity == score.total_score
        assert score.confidence >= 0.0 and score.confidence <= 1.0

    # ========== Integration Tests ==========
    
    @pytest.mark.asyncio
    async def test_scan_returns_filtered_results(self, scanner, sample_criteria):
        """Test that scan applies all filters correctly"""
        results = await scanner.scan_for_leads(sample_criteria)
        
        # Verify all results meet criteria
        for lead in results:
            assert lead.score.total_score >= sample_criteria.min_score
            assert lead.company.industry in sample_criteria.industries
            # Title should match one of the criteria
            title_matches = any(
                title.lower() in lead.contact.title.lower() 
                for title in sample_criteria.titles
            )
            assert title_matches, f"Title {lead.contact.title} doesn't match criteria"
    
    @pytest.mark.asyncio  
    async def test_scan_respects_max_results(self, scanner):
        """Test that max_results limit is enforced"""
        criteria = ScanCriteria(min_score=0, max_results=5)
        results = await scanner.scan_for_leads(criteria)
        
        assert len(results) <= 5, f"Expected max 5 results, got {len(results)}"
    
    @pytest.mark.asyncio
    async def test_scan_excludes_companies(self, scanner):
        """Test company exclusion list works"""
        # First get some companies
        criteria1 = ScanCriteria(min_score=0, max_results=10)
        initial_results = await scanner.scan_for_leads(criteria1)
        
        if len(initial_results) > 0:
            # Exclude first company
            excluded_company = initial_results[0].company.name
            
            criteria2 = ScanCriteria(
                min_score=0,
                max_results=10,
                exclude_companies=[excluded_company]
            )
            filtered_results = await scanner.scan_for_leads(criteria2)
            
            # Verify excluded company not in results
            company_names = [lead.company.name for lead in filtered_results]
            assert excluded_company not in company_names

    # ========== Performance Tests ==========
    
    @pytest.mark.asyncio
    async def test_scan_performance_under_1_second(self, scanner):
        """Test that scanning 1000 leads completes in <1 second"""
        criteria = ScanCriteria(min_score=0, max_results=50)  # Max available in mock
        
        start = time.time()
        results = await scanner.scan_for_leads(criteria)
        duration = time.time() - start
        
        assert duration < 1.0, f"Scan took {duration}s, expected <1s"
        assert len(results) <= 50

    # ========== Edge Case Tests ==========
    
    @pytest.mark.asyncio
    async def test_empty_criteria_returns_all_leads(self, scanner):
        """Test that empty criteria doesn't filter"""
        criteria = ScanCriteria(min_score=0)
        results = await scanner.scan_for_leads(criteria)
        
        assert len(results) > 0, "Empty criteria should return results"
    
    @pytest.mark.asyncio
    async def test_impossible_criteria_returns_empty(self, scanner):
        """Test that impossible criteria returns empty list"""
        criteria = ScanCriteria(
            industries=["NonExistentIndustry"],
            titles=["Impossible Title"],
            min_score=100  # Impossible score
        )
        results = await scanner.scan_for_leads(criteria)
        
        assert len(results) == 0, "Impossible criteria should return empty list"
    
    def test_malformed_input_handled_gracefully(self, scanner):
        """Test error handling for bad inputs"""
        # Test invalid min_score
        criteria = ScanCriteria(min_score=150)  # Will be clamped to 100
        assert criteria.min_score == 100
        
        # Test invalid max_results
        criteria = ScanCriteria(max_results=2000)  # Will be clamped to 1000
        assert criteria.max_results == 1000
        
        # Test negative values
        criteria = ScanCriteria(min_score=-10, max_results=-5)
        assert criteria.min_score == 0
        assert criteria.max_results == 1

    # ========== Scenario-Based Tests ==========
    
    @pytest.mark.asyncio
    async def test_scenario_find_series_a_saas_ctos(self, scanner):
        """Business scenario: Find CTOs at Series A SaaS companies"""
        criteria = ScanCriteria(
            industries=["SaaS"],
            titles=["CTO", "Chief Technology Officer"],
            keywords=["Series A"],
            min_score=75
        )
        
        results = await scanner.scan_for_leads(criteria)
        
        # Verify results match criteria
        for lead in results:
            assert lead.company.industry == "SaaS"
            assert any(title.upper() in lead.contact.title.upper() 
                      for title in ["CTO", "CHIEF TECHNOLOGY"])
            assert lead.score.total_score >= 75
            
    @pytest.mark.asyncio
    async def test_scenario_find_growing_fintech_vps(self, scanner):
        """Business scenario: Find VPs at growing FinTech companies"""
        criteria = ScanCriteria(
            industries=["FinTech"],
            titles=["VP", "Vice President"],
            company_sizes=["medium", "large"],  # 201-5000 employees
            min_score=65
        )
        
        results = await scanner.scan_for_leads(criteria)
        
        # Verify results
        for lead in results:
            assert lead.company.industry == "FinTech"
            assert "VP" in lead.contact.title.upper() or "VICE PRESIDENT" in lead.contact.title.upper()
            assert lead.score.total_score >= 65
            assert lead.company.employee_count >= 201  # Medium or large company

    # ========== Mode and Configuration Tests ==========
    
    def test_mode_switching(self):
        """Test different modes can be instantiated"""
        mock_scanner = LeadScannerAgent(mode="mock")
        assert mock_scanner.mode == "mock"
        
        hybrid_scanner = LeadScannerAgent(mode="hybrid")
        assert hybrid_scanner.mode == "hybrid"
        
        ai_scanner = LeadScannerAgent(mode="ai")
        assert ai_scanner.mode == "ai"
    
    def test_custom_scoring_weights(self):
        """Test custom scoring weight configuration"""
        custom_config = {
            'scoring_weights': {
                'industry_match': 40,
                'title_relevance': 30,
                'company_size_fit': 20,
                'recent_activity': 10
            }
        }
        scanner = LeadScannerAgent(mode="mock", config=custom_config)
        
        assert scanner.scoring_weights['industry_match'] == 40
        assert scanner.scoring_weights['title_relevance'] == 30

    # ========== Priority and Confidence Tests ==========
    
    def test_priority_assignment(self, scanner):
        """Test correct priority assignment based on scores"""
        assert scanner._determine_priority(85) == "high"
        assert scanner._determine_priority(70) == "medium"
        assert scanner._determine_priority(55) == "low"
    
    def test_confidence_calculation(self, scanner, sample_contact, sample_company):
        """Test confidence score calculation"""
        criteria = ScanCriteria()
        confidence = scanner._calculate_confidence(sample_contact, sample_company, criteria)
        
        assert 0.0 <= confidence <= 1.0
        # Sample contact/company have all fields, so confidence should be high
        assert confidence > 0.8

    # ========== Error Handling Tests ==========
    
    @pytest.mark.asyncio
    async def test_scan_handles_scoring_errors(self, scanner):
        """Test that scan continues even if individual lead scoring fails"""
        with patch.object(scanner, 'score_lead', side_effect=[Exception("Scoring error"), LeadScore(
            total_score=80,
            industry_match=30,
            title_relevance=30,
            company_size_fit=20,
            recent_activity=0,
            explanation="Test lead",
            confidence=0.9
        )]):
            criteria = ScanCriteria(min_score=0, max_results=10)
            # Should not raise exception
            results = await scanner.scan_for_leads(criteria)
    
    def test_score_lead_error_returns_zero_score(self, scanner, sample_contact):
        """Test that scoring errors return zero score instead of crashing"""
        # Create invalid company to trigger error
        invalid_company = Mock()
        invalid_company.industry = None  # This will cause an error
        
        criteria = ScanCriteria(industries=["SaaS"])
        score = scanner.score_lead(sample_contact, invalid_company, criteria)
        
        assert score.total_score == 0
        assert "Error" in score.explanation

    # ========== Logging Tests ==========
    
    @pytest.mark.asyncio
    async def test_logging_metrics(self, scanner, caplog):
        """Test that scan logs appropriate metrics"""
        import logging
        scanner.logger.setLevel(logging.INFO)
        
        criteria = ScanCriteria(min_score=0, max_results=5)
        results = await scanner.scan_for_leads(criteria)
        
        # Check that metrics were logged
        assert "Scan completed" in caplog.text
        assert "leads found" in caplog.text

    # ========== Validation Tests ==========
    
    def test_lead_id_validation(self):
        """Test Lead model validates ID format"""
        with pytest.raises(ValueError):
            Lead(
                lead_id="invalid_id",  # Should start with "lead_"
                contact=Mock(),
                company=Mock(),
                score=Mock(),
                discovered_at=datetime.now(),
                source="mock",
                outreach_priority="high"
            )
    
    def test_score_validation(self):
        """Test LeadScore validates ranges"""
        score = LeadScore(
            total_score=150,  # Should be clamped to 100
            industry_match=50,  # Should be clamped to 100
            title_relevance=30,
            company_size_fit=20,
            recent_activity=20,
            explanation="Test",
            confidence=1.5  # Should be clamped to 1.0
        )
        
        assert score.total_score == 100
        assert score.industry_match == 100
        assert score.confidence == 1.0