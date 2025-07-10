#!/usr/bin/env python3
"""
HubSpot CRM Integration for HeyJarvis
Real-time access to contacts, companies, and deals with caching and rate limiting
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib

from hubspot import HubSpot
from hubspot.crm.contacts import ApiException as ContactsApiException
from hubspot.crm.companies import ApiException as CompaniesApiException
from hubspot.crm.deals import ApiException as DealsApiException
import redis.asyncio as redis
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SearchOperator(Enum):
    """HubSpot search operators"""
    EQ = "EQ"  # Equal to
    NEQ = "NEQ"  # Not equal to
    LT = "LT"  # Less than
    LTE = "LTE"  # Less than or equal to
    GT = "GT"  # Greater than
    GTE = "GTE"  # Greater than or equal to
    HAS_PROPERTY = "HAS_PROPERTY"  # Has property value
    NOT_HAS_PROPERTY = "NOT_HAS_PROPERTY"  # Doesn't have property value
    CONTAINS_TOKEN = "CONTAINS_TOKEN"  # Contains token
    NOT_CONTAINS_TOKEN = "NOT_CONTAINS_TOKEN"  # Doesn't contain token
    IN = "IN"  # In list
    NOT_IN = "NOT_IN"  # Not in list


@dataclass
class HubSpotContact:
    """HubSpot contact data"""
    id: str
    email: Optional[str]
    firstname: Optional[str]
    lastname: Optional[str]
    company: Optional[str]
    jobtitle: Optional[str]
    phone: Optional[str]
    website: Optional[str]
    lifecyclestage: Optional[str]
    hs_lead_status: Optional[str]
    notes_last_updated: Optional[datetime]
    notes_last_contacted: Optional[datetime]
    hs_email_open: Optional[int]
    hs_email_click: Optional[int]
    num_contacted_notes: Optional[int]
    num_notes: Optional[int]
    hs_analytics_num_page_views: Optional[int]
    hs_analytics_num_visits: Optional[int]
    hs_analytics_num_event_completions: Optional[int]
    createdate: Optional[datetime]
    lastmodifieddate: Optional[datetime]
    custom_properties: Dict[str, Any]


@dataclass
class HubSpotCompany:
    """HubSpot company data"""
    id: str
    name: Optional[str]
    domain: Optional[str]
    industry: Optional[str]
    numberofemployees: Optional[int]
    annualrevenue: Optional[float]
    city: Optional[str]
    state: Optional[str]
    country: Optional[str]
    description: Optional[str]
    website: Optional[str]
    phone: Optional[str]
    type: Optional[str]
    createdate: Optional[datetime]
    hs_lastmodifieddate: Optional[datetime]
    custom_properties: Dict[str, Any]


@dataclass
class HubSpotDeal:
    """HubSpot deal data"""
    id: str
    dealname: Optional[str]
    dealstage: Optional[str]
    amount: Optional[float]
    closedate: Optional[datetime]
    probability: Optional[float]
    pipeline: Optional[str]
    hs_forecast_category: Optional[str]
    hs_is_closed: Optional[bool]
    hs_is_closed_won: Optional[bool]
    createdate: Optional[datetime]
    hs_lastmodifieddate: Optional[datetime]


class HubSpotIntegration:
    """
    HubSpot CRM integration with caching and rate limiting
    Features:
    - Real-time access to contacts, companies, and deals
    - Advanced search with filtering
    - Redis caching for performance
    - Rate limiting (10 requests/second)
    - Batch operations
    - Pagination handling
    """
    
    def __init__(self, access_token: Optional[str] = None, redis_client: Optional[redis.Redis] = None):
        """
        Initialize HubSpot integration
        
        Args:
            access_token: HubSpot API access token
            redis_client: Redis client for caching
        """
        self.access_token = access_token or os.getenv("HUBSPOT_ACCESS_TOKEN")
        self.api_client = None
        self.redis_client = redis_client
        
        # Rate limiting
        self.rate_limiter = asyncio.Semaphore(10)  # 10 requests per second
        self.last_request_time = datetime.utcnow()
        
        # Cache settings
        self.cache_ttl = 3600  # 1 hour
        self.cache_prefix = "hubspot:"
        
        if self.access_token:
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize HubSpot API client"""
        try:
            self.api_client = HubSpot(access_token=self.access_token)
            logger.info("HubSpot API client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize HubSpot client: {e}")
            raise
    
    def update_access_token(self, access_token: str):
        """Update access token and reinitialize client"""
        self.access_token = access_token
        self._initialize_client()
    
    async def _rate_limit(self):
        """Enforce rate limiting"""
        async with self.rate_limiter:
            # Ensure minimum 100ms between requests
            elapsed = (datetime.utcnow() - self.last_request_time).total_seconds()
            if elapsed < 0.1:
                await asyncio.sleep(0.1 - elapsed)
            self.last_request_time = datetime.utcnow()
    
    def _cache_key(self, prefix: str, params: Dict[str, Any]) -> str:
        """Generate cache key from parameters"""
        # Create a deterministic string from params
        param_str = json.dumps(params, sort_keys=True)
        param_hash = hashlib.md5(param_str.encode()).hexdigest()
        return f"{self.cache_prefix}{prefix}:{param_hash}"
    
    async def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get data from cache"""
        if not self.redis_client:
            return None
        
        try:
            data = await self.redis_client.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
        
        return None
    
    async def _set_cache(self, key: str, data: Any, ttl: Optional[int] = None):
        """Set data in cache"""
        if not self.redis_client:
            return
        
        try:
            await self.redis_client.setex(
                key,
                ttl or self.cache_ttl,
                json.dumps(data, default=str)
            )
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
    
    async def _invalidate_cache_pattern(self, pattern: str):
        """Invalidate cache entries matching pattern"""
        if not self.redis_client:
            return
        
        try:
            async for key in self.redis_client.scan_iter(match=f"{self.cache_prefix}{pattern}*"):
                await self.redis_client.delete(key)
        except Exception as e:
            logger.warning(f"Cache invalidation error: {e}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(Exception)
    )
    async def search_contacts(
        self,
        filters: Optional[List[Dict[str, Any]]] = None,
        search_term: Optional[str] = None,
        properties: Optional[List[str]] = None,
        limit: int = 100,
        after: Optional[str] = None,
        sorts: Optional[List[Dict[str, str]]] = None
    ) -> Tuple[List[HubSpotContact], Optional[str]]:
        """
        Search contacts with advanced filtering
        
        Args:
            filters: List of filter groups (OR between groups, AND within groups)
            search_term: Text search term
            properties: Properties to return
            limit: Number of results per page
            after: Pagination cursor
            sorts: Sort criteria
            
        Returns:
            Tuple of (contacts, next_page_cursor)
        """
        await self._rate_limit()
        
        # Check cache
        cache_params = {
            "filters": filters,
            "search_term": search_term,
            "properties": properties,
            "limit": limit,
            "after": after,
            "sorts": sorts
        }
        cache_key = self._cache_key("contacts_search", cache_params)
        cached_data = await self._get_from_cache(cache_key)
        if cached_data:
            logger.info("Returning cached contact search results")
            return (
                [HubSpotContact(**c) for c in cached_data["contacts"]],
                cached_data.get("after")
            )
        
        # Default properties
        if not properties:
            properties = [
                "email", "firstname", "lastname", "company", "jobtitle",
                "phone", "website", "lifecyclestage", "hs_lead_status",
                "notes_last_updated", "notes_last_contacted",
                "hs_email_open", "hs_email_click",
                "num_contacted_notes", "num_notes",
                "hs_analytics_num_page_views", "hs_analytics_num_visits",
                "hs_analytics_num_event_completions",
                "createdate", "lastmodifieddate"
            ]
        
        try:
            # Build search request
            search_request = {
                "filterGroups": filters or [],
                "properties": properties,
                "limit": min(limit, 100),  # HubSpot max is 100
                "after": after
            }
            
            if search_term:
                search_request["query"] = search_term
            
            if sorts:
                search_request["sorts"] = sorts
            
            # Execute search
            api_response = self.api_client.crm.contacts.search_api.do_search(
                public_object_search_request=search_request
            )
            
            # Parse results
            contacts = []
            for result in api_response.results:
                contact_data = {
                    "id": result.id,
                    "custom_properties": {}
                }
                
                # Extract properties
                for prop, value in result.properties.items():
                    if prop in ["email", "firstname", "lastname", "company", 
                               "jobtitle", "phone", "website", "lifecyclestage", 
                               "hs_lead_status"]:
                        contact_data[prop] = value
                    elif prop in ["hs_email_open", "hs_email_click", 
                                 "num_contacted_notes", "num_notes",
                                 "hs_analytics_num_page_views", "hs_analytics_num_visits",
                                 "hs_analytics_num_event_completions"]:
                        contact_data[prop] = int(value) if value else None
                    elif prop in ["notes_last_updated", "notes_last_contacted",
                                 "createdate", "lastmodifieddate"]:
                        contact_data[prop] = datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None
                    else:
                        contact_data["custom_properties"][prop] = value
                
                contacts.append(HubSpotContact(**contact_data))
            
            # Get next page cursor
            next_after = None
            if hasattr(api_response, 'paging') and api_response.paging:
                next_after = api_response.paging.next.after if api_response.paging.next else None
            
            # Cache results
            cache_data = {
                "contacts": [asdict(c) for c in contacts],
                "after": next_after
            }
            await self._set_cache(cache_key, cache_data)
            
            logger.info(f"Found {len(contacts)} contacts")
            return contacts, next_after
            
        except ContactsApiException as e:
            logger.error(f"HubSpot contacts API error: {e}")
            if e.status == 429:  # Rate limit
                retry_after = int(e.headers.get('Retry-After', 60))
                logger.warning(f"Rate limited, retry after {retry_after}s")
                await asyncio.sleep(retry_after)
                raise
            raise
    
    async def get_companies(
        self,
        filters: Optional[List[Dict[str, Any]]] = None,
        properties: Optional[List[str]] = None,
        limit: int = 100,
        after: Optional[str] = None
    ) -> Tuple[List[HubSpotCompany], Optional[str]]:
        """
        Get companies with filtering
        
        Args:
            filters: Filter criteria
            properties: Properties to return
            limit: Number of results
            after: Pagination cursor
            
        Returns:
            Tuple of (companies, next_page_cursor)
        """
        await self._rate_limit()
        
        # Check cache
        cache_params = {
            "filters": filters,
            "properties": properties,
            "limit": limit,
            "after": after
        }
        cache_key = self._cache_key("companies", cache_params)
        cached_data = await self._get_from_cache(cache_key)
        if cached_data:
            logger.info("Returning cached companies")
            return (
                [HubSpotCompany(**c) for c in cached_data["companies"]],
                cached_data.get("after")
            )
        
        # Default properties
        if not properties:
            properties = [
                "name", "domain", "industry", "numberofemployees",
                "annualrevenue", "city", "state", "country",
                "description", "website", "phone", "type",
                "createdate", "hs_lastmodifieddate"
            ]
        
        try:
            if filters:
                # Use search API for filtering
                search_request = {
                    "filterGroups": filters,
                    "properties": properties,
                    "limit": min(limit, 100),
                    "after": after
                }
                
                api_response = self.api_client.crm.companies.search_api.do_search(
                    public_object_search_request=search_request
                )
            else:
                # Use basic API without filters
                api_response = self.api_client.crm.companies.basic_api.get_page(
                    limit=min(limit, 100),
                    properties=properties,
                    after=after
                )
            
            # Parse results
            companies = []
            for result in api_response.results:
                company_data = {
                    "id": result.id,
                    "custom_properties": {}
                }
                
                # Extract properties
                for prop, value in result.properties.items():
                    if prop in ["name", "domain", "industry", "city", "state",
                               "country", "description", "website", "phone", "type"]:
                        company_data[prop] = value
                    elif prop == "numberofemployees":
                        company_data[prop] = int(value) if value else None
                    elif prop == "annualrevenue":
                        company_data[prop] = float(value) if value else None
                    elif prop in ["createdate", "hs_lastmodifieddate"]:
                        company_data[prop] = datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None
                    else:
                        company_data["custom_properties"][prop] = value
                
                companies.append(HubSpotCompany(**company_data))
            
            # Get next page cursor
            next_after = None
            if hasattr(api_response, 'paging') and api_response.paging:
                next_after = api_response.paging.next.after if api_response.paging.next else None
            
            # Cache results
            cache_data = {
                "companies": [asdict(c) for c in companies],
                "after": next_after
            }
            await self._set_cache(cache_key, cache_data)
            
            logger.info(f"Found {len(companies)} companies")
            return companies, next_after
            
        except CompaniesApiException as e:
            logger.error(f"HubSpot companies API error: {e}")
            raise
    
    async def create_contact(
        self,
        email: str,
        properties: Dict[str, Any],
        associations: Optional[Dict[str, List[str]]] = None
    ) -> HubSpotContact:
        """
        Create a new contact
        
        Args:
            email: Contact email
            properties: Contact properties
            associations: Associations to other objects (e.g., {"companies": ["123"]})
            
        Returns:
            Created contact
        """
        await self._rate_limit()
        
        try:
            # Add email to properties
            properties["email"] = email
            
            # Create contact
            contact_input = {
                "properties": properties
            }
            
            if associations:
                contact_input["associations"] = []
                for object_type, ids in associations.items():
                    for object_id in ids:
                        contact_input["associations"].append({
                            "to": {"id": object_id},
                            "types": [{"associationCategory": "HUBSPOT_DEFINED",
                                     "associationTypeId": self._get_association_type_id("contact", object_type)}]
                        })
            
            api_response = self.api_client.crm.contacts.basic_api.create(
                simple_public_object_input_for_create=contact_input
            )
            
            # Invalidate search cache
            await self._invalidate_cache_pattern("contacts_search")
            
            # Parse response
            contact_data = {
                "id": api_response.id,
                "email": email,
                "custom_properties": {}
            }
            
            for prop, value in api_response.properties.items():
                if prop in ["firstname", "lastname", "company", "jobtitle", "phone", "website"]:
                    contact_data[prop] = value
                elif prop not in ["email"]:
                    contact_data["custom_properties"][prop] = value
            
            logger.info(f"Created contact: {email}")
            return HubSpotContact(**contact_data)
            
        except ContactsApiException as e:
            logger.error(f"Failed to create contact: {e}")
            raise
    
    async def update_contact(
        self,
        contact_id: str,
        properties: Dict[str, Any]
    ) -> HubSpotContact:
        """
        Update contact properties
        
        Args:
            contact_id: Contact ID
            properties: Properties to update
            
        Returns:
            Updated contact
        """
        await self._rate_limit()
        
        try:
            # Update contact
            api_response = self.api_client.crm.contacts.basic_api.update(
                contact_id=contact_id,
                simple_public_object_input={"properties": properties}
            )
            
            # Invalidate caches
            await self._invalidate_cache_pattern("contacts_search")
            await self._invalidate_cache_pattern(f"contact:{contact_id}")
            
            # Parse response
            contact_data = {
                "id": api_response.id,
                "custom_properties": {}
            }
            
            for prop, value in api_response.properties.items():
                if prop in ["email", "firstname", "lastname", "company", 
                           "jobtitle", "phone", "website", "lifecyclestage"]:
                    contact_data[prop] = value
                else:
                    contact_data["custom_properties"][prop] = value
            
            logger.info(f"Updated contact: {contact_id}")
            return HubSpotContact(**contact_data)
            
        except ContactsApiException as e:
            logger.error(f"Failed to update contact: {e}")
            raise
    
    async def get_contact_by_email(self, email: str) -> Optional[HubSpotContact]:
        """Get contact by email address"""
        contacts, _ = await self.search_contacts(
            filters=[{
                "filters": [{
                    "propertyName": "email",
                    "operator": "EQ",
                    "value": email
                }]
            }],
            limit=1
        )
        
        return contacts[0] if contacts else None
    
    async def get_contacts_by_company(
        self,
        company_id: str,
        limit: int = 100
    ) -> List[HubSpotContact]:
        """Get all contacts associated with a company"""
        await self._rate_limit()
        
        try:
            # Get associations
            api_response = self.api_client.crm.companies.associations_api.get_all(
                company_id=company_id,
                to_object_type="contacts",
                limit=limit
            )
            
            # Get contact IDs
            contact_ids = [result.to_object_id for result in api_response.results]
            
            if not contact_ids:
                return []
            
            # Batch get contacts
            contacts = await self.batch_get_contacts(contact_ids)
            
            return contacts
            
        except CompaniesApiException as e:
            logger.error(f"Failed to get contacts for company: {e}")
            return []
    
    async def batch_get_contacts(
        self,
        contact_ids: List[str],
        properties: Optional[List[str]] = None
    ) -> List[HubSpotContact]:
        """Get multiple contacts by ID"""
        if not contact_ids:
            return []
        
        await self._rate_limit()
        
        # Default properties
        if not properties:
            properties = [
                "email", "firstname", "lastname", "company", "jobtitle",
                "phone", "website", "lifecyclestage", "hs_lead_status"
            ]
        
        try:
            # Batch read (max 100 at a time)
            contacts = []
            for i in range(0, len(contact_ids), 100):
                batch_ids = contact_ids[i:i+100]
                
                api_response = self.api_client.crm.contacts.batch_api.read(
                    batch_read_input_simple_public_object_id={
                        "properties": properties,
                        "inputs": [{"id": cid} for cid in batch_ids]
                    }
                )
                
                for result in api_response.results:
                    contact_data = {
                        "id": result.id,
                        "custom_properties": {}
                    }
                    
                    for prop, value in result.properties.items():
                        if prop in ["email", "firstname", "lastname", "company",
                                   "jobtitle", "phone", "website", "lifecyclestage",
                                   "hs_lead_status"]:
                            contact_data[prop] = value
                        else:
                            contact_data["custom_properties"][prop] = value
                    
                    contacts.append(HubSpotContact(**contact_data))
            
            return contacts
            
        except ContactsApiException as e:
            logger.error(f"Failed to batch get contacts: {e}")
            return []
    
    async def get_contact_deals(
        self,
        contact_id: str,
        limit: int = 100
    ) -> List[HubSpotDeal]:
        """Get deals associated with a contact"""
        await self._rate_limit()
        
        try:
            # Get associations
            api_response = self.api_client.crm.contacts.associations_api.get_all(
                contact_id=contact_id,
                to_object_type="deals",
                limit=limit
            )
            
            # Get deal IDs
            deal_ids = [result.to_object_id for result in api_response.results]
            
            if not deal_ids:
                return []
            
            # Get deal details
            deals = []
            properties = [
                "dealname", "dealstage", "amount", "closedate",
                "probability", "pipeline", "hs_forecast_category",
                "hs_is_closed", "hs_is_closed_won",
                "createdate", "hs_lastmodifieddate"
            ]
            
            api_response = self.api_client.crm.deals.batch_api.read(
                batch_read_input_simple_public_object_id={
                    "properties": properties,
                    "inputs": [{"id": did} for did in deal_ids[:100]]  # Max 100
                }
            )
            
            for result in api_response.results:
                deal_data = {"id": result.id}
                
                for prop, value in result.properties.items():
                    if prop in ["dealname", "dealstage", "pipeline", "hs_forecast_category"]:
                        deal_data[prop] = value
                    elif prop == "amount":
                        deal_data[prop] = float(value) if value else None
                    elif prop == "probability":
                        deal_data[prop] = float(value) / 100 if value else None
                    elif prop in ["hs_is_closed", "hs_is_closed_won"]:
                        deal_data[prop] = value == "true" if value else False
                    elif prop in ["closedate", "createdate", "hs_lastmodifieddate"]:
                        deal_data[prop] = datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None
                
                deals.append(HubSpotDeal(**deal_data))
            
            return deals
            
        except (ContactsApiException, DealsApiException) as e:
            logger.error(f"Failed to get contact deals: {e}")
            return []
    
    def _get_association_type_id(self, from_object: str, to_object: str) -> int:
        """Get HubSpot association type ID"""
        association_types = {
            ("contact", "company"): 279,
            ("company", "contact"): 280,
            ("contact", "deal"): 3,
            ("deal", "contact"): 4,
            ("company", "deal"): 341,
            ("deal", "company"): 342
        }
        
        return association_types.get((from_object, to_object), 1)
    
    async def search_contacts_by_criteria(
        self,
        title_keywords: Optional[List[str]] = None,
        industries: Optional[List[str]] = None,
        company_size_min: Optional[int] = None,
        company_size_max: Optional[int] = None,
        last_activity_days: Optional[int] = None,
        min_email_opens: Optional[int] = None,
        lifecycle_stages: Optional[List[str]] = None,
        custom_filters: Optional[List[Dict[str, Any]]] = None,
        limit: int = 100
    ) -> List[HubSpotContact]:
        """
        Search contacts by multiple criteria
        
        Args:
            title_keywords: Keywords to search in job title
            industries: List of industries
            company_size_min: Minimum company size
            company_size_max: Maximum company size
            last_activity_days: Contacts active in last N days
            min_email_opens: Minimum email opens
            lifecycle_stages: Filter by lifecycle stages
            custom_filters: Additional custom filters
            limit: Maximum results
            
        Returns:
            List of matching contacts
        """
        # Build filter groups
        filter_groups = []
        
        # Title keywords filter (OR between keywords)
        if title_keywords:
            title_filters = []
            for keyword in title_keywords:
                title_filters.append({
                    "propertyName": "jobtitle",
                    "operator": "CONTAINS_TOKEN",
                    "value": keyword
                })
            
            if title_filters:
                filter_groups.append({"filters": title_filters})
        
        # Industry filter
        if industries:
            filter_groups.append({
                "filters": [{
                    "propertyName": "industry",
                    "operator": "IN",
                    "values": industries
                }]
            })
        
        # Company size filters
        size_filters = []
        if company_size_min is not None:
            size_filters.append({
                "propertyName": "numberofemployees",
                "operator": "GTE",
                "value": str(company_size_min)
            })
        if company_size_max is not None:
            size_filters.append({
                "propertyName": "numberofemployees",
                "operator": "LTE",
                "value": str(company_size_max)
            })
        
        if size_filters:
            filter_groups.append({"filters": size_filters})
        
        # Last activity filter
        if last_activity_days:
            cutoff_date = datetime.utcnow() - timedelta(days=last_activity_days)
            filter_groups.append({
                "filters": [{
                    "propertyName": "notes_last_contacted",
                    "operator": "GTE",
                    "value": cutoff_date.isoformat()
                }]
            })
        
        # Email engagement filter
        if min_email_opens is not None:
            filter_groups.append({
                "filters": [{
                    "propertyName": "hs_email_open",
                    "operator": "GTE",
                    "value": str(min_email_opens)
                }]
            })
        
        # Lifecycle stage filter
        if lifecycle_stages:
            filter_groups.append({
                "filters": [{
                    "propertyName": "lifecyclestage",
                    "operator": "IN",
                    "values": lifecycle_stages
                }]
            })
        
        # Add custom filters
        if custom_filters:
            filter_groups.extend(custom_filters)
        
        # Sort by engagement
        sorts = [{
            "propertyName": "hs_analytics_num_page_views",
            "direction": "DESCENDING"
        }]
        
        # Search contacts
        all_contacts = []
        after = None
        
        while len(all_contacts) < limit:
            contacts, after = await self.search_contacts(
                filters=filter_groups if filter_groups else None,
                sorts=sorts,
                limit=min(100, limit - len(all_contacts)),
                after=after
            )
            
            all_contacts.extend(contacts)
            
            if not after:
                break
        
        return all_contacts[:limit]
    
    async def calculate_activity_score(self, contact: HubSpotContact) -> float:
        """
        Calculate activity-based score for a contact
        
        Returns:
            Activity score between 0 and 100
        """
        score = 0.0
        
        # Email engagement (0-30 points)
        if contact.hs_email_open:
            score += min(contact.hs_email_open * 2, 15)
        if contact.hs_email_click:
            score += min(contact.hs_email_click * 5, 15)
        
        # Website activity (0-30 points)
        if contact.hs_analytics_num_page_views:
            score += min(contact.hs_analytics_num_page_views * 0.5, 15)
        if contact.hs_analytics_num_visits:
            score += min(contact.hs_analytics_num_visits * 2, 15)
        
        # Recent activity (0-20 points)
        if contact.notes_last_contacted:
            days_since_contact = (datetime.utcnow() - contact.notes_last_contacted).days
            if days_since_contact <= 7:
                score += 20
            elif days_since_contact <= 30:
                score += 15
            elif days_since_contact <= 90:
                score += 10
            elif days_since_contact <= 180:
                score += 5
        
        # Interaction frequency (0-20 points)
        if contact.num_notes:
            score += min(contact.num_notes * 2, 10)
        if contact.num_contacted_notes:
            score += min(contact.num_contacted_notes * 2.5, 10)
        
        # Check for associated deals
        try:
            deals = await self.get_contact_deals(contact.id)
            if deals:
                # Has deals (0-20 bonus points)
                score += 10
                
                # Open deals
                open_deals = [d for d in deals if not d.hs_is_closed]
                if open_deals:
                    score += 5
                
                # Won deals
                won_deals = [d for d in deals if d.hs_is_closed_won]
                if won_deals:
                    score += 5
        except Exception as e:
            logger.warning(f"Failed to get deals for contact {contact.id}: {e}")
        
        return min(score, 100.0)


# Example usage
async def main():
    """Example usage of HubSpot integration"""
    
    # Initialize Redis
    redis_client = await redis.from_url("redis://localhost:6379")
    
    # Initialize HubSpot integration
    hubspot = HubSpotIntegration(
        access_token="your-access-token",
        redis_client=redis_client
    )
    
    try:
        # Search for VP/Director level contacts in SaaS companies
        contacts = await hubspot.search_contacts_by_criteria(
            title_keywords=["VP", "Director", "Head"],
            industries=["Software", "Technology", "SaaS"],
            company_size_min=50,
            company_size_max=500,
            last_activity_days=90,
            min_email_opens=5,
            lifecycle_stages=["lead", "marketingqualifiedlead"],
            limit=20
        )
        
        print(f"Found {len(contacts)} matching contacts")
        
        # Calculate activity scores
        for contact in contacts[:5]:
            score = await hubspot.calculate_activity_score(contact)
            print(f"\n{contact.firstname} {contact.lastname} ({contact.jobtitle})")
            print(f"  Company: {contact.company}")
            print(f"  Email: {contact.email}")
            print(f"  Activity Score: {score:.1f}/100")
        
        # Create a new contact
        new_contact = await hubspot.create_contact(
            email="test@example.com",
            properties={
                "firstname": "Test",
                "lastname": "User",
                "company": "Test Company",
                "jobtitle": "VP Sales"
            }
        )
        print(f"\nCreated contact: {new_contact.id}")
        
    finally:
        await redis_client.close()


if __name__ == "__main__":
    asyncio.run(main())