#!/usr/bin/env python3
"""
MSA (Master Service Agreement) Parser Module
Extracts structured data from MSA documents according to a predefined schema.
"""

import json
import re
import logging
import time
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

# MSA Schema Definition
MSA_SCHEMA = {
    "name": "MASTER SERVICE AGREEMENT",
    "description": "Top-level MSA object",
    "mandatory": True,
    "object_type": "obj",
    "is_list": False,
    "fields": [
        {"field_name": "msa_id", "field_description": "unique identifier for the MSA", "mandatory": True, "object_type": "string"},
        {"field_name": "version", "field_description": "version number of the MSA", "mandatory": False, "object_type": "string"},
        {"field_name": "effective_date", "field_description": "date when MSA becomes effective", "mandatory": True, "object_type": "date"},
        {"field_name": "executed_date", "field_description": "date the MSA was executed", "mandatory": True, "object_type": "date"},
        {"field_name": "expiration_date", "field_description": "expiration date of the MSA", "mandatory": False, "object_type": "date"},
        {"field_name": "auto_renewal", "field_description": "whether MSA auto-renews", "mandatory": False, "object_type": "boolean"},
        {"field_name": "renewal_term", "field_description": "renewal term period if auto-renewal is enabled", "mandatory": False, "object_type": "string"},
        {"field_name": "msa_type", "field_description": "contracts providing different types of services might have different sections/exhibits (e.g. IT services, warehousing, labor services)", "mandatory": False, "object_type": "string"},
        {"field_name": "nature_of_services", "field_description": "the type of service being offered as part of the MSA", "mandatory": True, "object_type": "string"},
        {"field_name": "billing_currency", "field_description": "currency for billing", "mandatory": False, "object_type": "string"},
        {"field_name": "governing_law", "field_description": "governing law jurisdiction", "mandatory": True, "object_type": "string"},
        {"field_name": "jurisdiction", "field_description": "legal jurisdiction for disputes", "mandatory": False, "object_type": "string"}
    ],
    "children": [
        {
            "name": "customer",
            "description": "customer party to the MSA",
            "mandatory": True,
            "object_type": "obj",
            "is_list": False,
            "fields": [
                {"field_name": "legal_name", "field_description": "legal name of the customer entity", "mandatory": True, "object_type": "string"},
                {"field_name": "dba_name", "field_description": "doing business as name", "mandatory": False, "object_type": "string"},
                {"field_name": "entity_type", "field_description": "type of legal entity", "mandatory": False, "object_type": "enum", "enum_values": ["Corporation", "LLC", "Partnership", "Sole Proprietorship", "Non-Profit", "Government Agency", "Other"]},
                {"field_name": "tax_id", "field_description": "tax identification number", "mandatory": False, "object_type": "string"},
                {"field_name": "registration_number", "field_description": "company registration number", "mandatory": False, "object_type": "string"}
            ],
            "children": [
                {
                    "name": "registered_address",
                    "description": "registered business address",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": False,
                    "fields": [
                        {"field_name": "street_address", "field_description": "street address", "mandatory": False, "object_type": "string"},
                        {"field_name": "city", "field_description": "city", "mandatory": False, "object_type": "string"},
                        {"field_name": "state_province", "field_description": "state or province", "mandatory": False, "object_type": "string"},
                        {"field_name": "postal_code", "field_description": "postal or zip code", "mandatory": False, "object_type": "string"},
                        {"field_name": "country", "field_description": "country", "mandatory": False, "object_type": "string"}
                    ]
                },
                {
                    "name": "billing_address",
                    "description": "billing address if different from registered",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": False,
                    "fields": [
                        {"field_name": "street_address", "field_description": "street address", "mandatory": False, "object_type": "string"},
                        {"field_name": "city", "field_description": "city", "mandatory": False, "object_type": "string"},
                        {"field_name": "state_province", "field_description": "state or province", "mandatory": False, "object_type": "string"},
                        {"field_name": "postal_code", "field_description": "postal or zip code", "mandatory": False, "object_type": "string"},
                        {"field_name": "country", "field_description": "country", "mandatory": False, "object_type": "string"}
                    ]
                },
                {
                    "name": "primary_contact",
                    "description": "primary contact person",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": False,
                    "fields": [
                        {"field_name": "name", "field_description": "full name", "mandatory": False, "object_type": "string"},
                        {"field_name": "title", "field_description": "job title", "mandatory": False, "object_type": "string"},
                        {"field_name": "email", "field_description": "email address", "mandatory": False, "object_type": "string"},
                        {"field_name": "phone", "field_description": "phone number", "mandatory": False, "object_type": "string"},
                        {"field_name": "mobile", "field_description": "mobile number", "mandatory": False, "object_type": "string"}
                    ]
                },
                {
                    "name": "authorized_signatory",
                    "description": "authorized signatory for the customer",
                    "mandatory": True,
                    "object_type": "obj",
                    "is_list": False,
                    "fields": [
                        {"field_name": "name", "field_description": "full name", "mandatory": True, "object_type": "string"},
                        {"field_name": "title", "field_description": "job title", "mandatory": False, "object_type": "string"},
                        {"field_name": "email", "field_description": "email address", "mandatory": False, "object_type": "string"},
                        {"field_name": "signature_date", "field_description": "date of signature", "mandatory": False, "object_type": "date"}
                    ]
                }
            ]
        },
        {
            "name": "provider",
            "description": "provider/vendor party to the MSA",
            "mandatory": True,
            "object_type": "obj",
            "is_list": False,
            "fields": [
                {"field_name": "legal_name", "field_description": "legal name of the provider entity", "mandatory": True, "object_type": "string"},
                {"field_name": "dba_name", "field_description": "doing business as name", "mandatory": False, "object_type": "string"},
                {"field_name": "entity_type", "field_description": "type of legal entity", "mandatory": False, "object_type": "enum", "enum_values": ["Corporation", "LLC", "Partnership", "Sole Proprietorship", "Non-Profit", "Other"]},
                {"field_name": "tax_id", "field_description": "tax identification number", "mandatory": False, "object_type": "string"},
                {"field_name": "registration_number", "field_description": "company registration number", "mandatory": False, "object_type": "string"}
            ],
            "children": [
                {
                    "name": "registered_address",
                    "description": "registered business address",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": False,
                    "fields": [
                        {"field_name": "street_address", "field_description": "street address", "mandatory": False, "object_type": "string"},
                        {"field_name": "city", "field_description": "city", "mandatory": False, "object_type": "string"},
                        {"field_name": "state_province", "field_description": "state or province", "mandatory": False, "object_type": "string"},
                        {"field_name": "postal_code", "field_description": "postal or zip code", "mandatory": False, "object_type": "string"},
                        {"field_name": "country", "field_description": "country", "mandatory": False, "object_type": "string"}
                    ]
                },
                {
                    "name": "primary_contact",
                    "description": "primary contact person",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": False,
                    "fields": [
                        {"field_name": "name", "field_description": "full name", "mandatory": False, "object_type": "string"},
                        {"field_name": "title", "field_description": "job title", "mandatory": False, "object_type": "string"},
                        {"field_name": "email", "field_description": "email address", "mandatory": False, "object_type": "string"},
                        {"field_name": "phone", "field_description": "phone number", "mandatory": False, "object_type": "string"}
                    ]
                },
                {
                    "name": "authorized_signatory",
                    "description": "authorized signatory for the provider",
                    "mandatory": True,
                    "object_type": "obj",
                    "is_list": False,
                    "fields": [
                        {"field_name": "name", "field_description": "full name", "mandatory": True, "object_type": "string"},
                        {"field_name": "title", "field_description": "job title", "mandatory": False, "object_type": "string"},
                        {"field_name": "email", "field_description": "email address", "mandatory": False, "object_type": "string"},
                        {"field_name": "signature_date", "field_description": "date of signature", "mandatory": False, "object_type": "date"}
                    ]
                }
            ]
        },
        {
            "name": "services_scope",
            "description": "scope of services covered under MSA",
            "mandatory": True,
            "object_type": "obj",
            "is_list": False,
            "fields": [],
            "children": [
                {
                    "name": "service_categories",
                    "description": "categories of services that can be provided",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": True,
                    "fields": [
                        {"field_name": "value", "field_description": "service category", "mandatory": False, "object_type": "enum", "enum_values": ["Software Development", "IT Consulting", "Cloud Services", "Data Analytics", "Cybersecurity", "Managed Services", "Professional Services", "Staff Augmentation", "Training", "Maintenance and Support"]}
                    ]
                },
                {
                    "name": "excluded_services",
                    "description": "services explicitly excluded from MSA",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": False,
                    "fields": [
                        {"field_name": "value", "field_description": "free text of excluded services", "mandatory": False, "object_type": "string"}
                    ]
                },
                {
                    "name": "service_locations",
                    "description": "locations where services can be performed",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": True,
                    "fields": [
                        {"field_name": "value", "field_description": "location mode", "mandatory": False, "object_type": "enum", "enum_values": ["On-site", "Remote", "Provider Facility", "Hybrid"]}
                    ]
                }
            ]
        },
        {
            "name": "commercial_terms",
            "description": "commercial and pricing terms",
            "mandatory": False,
            "object_type": "obj",
            "is_list": False,
            "fields": [],
            "children": [
                {
                    "name": "rate_cards",
                    "description": "standard rate cards for different services",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": True,
                    "fields": [
                        {"field_name": "service_type", "field_description": "type of service", "mandatory": False, "object_type": "string"},
                        {"field_name": "resource_level", "field_description": "resource seniority level", "mandatory": False, "object_type": "enum", "enum_values": ["Junior", "Mid-level", "Senior", "Expert", "Principal", "Executive"]},
                        {"field_name": "hourly_rate", "field_description": "standard hourly rate", "mandatory": False, "object_type": "numeric"},
                        {"field_name": "daily_rate", "field_description": "standard daily rate", "mandatory": False, "object_type": "numeric"},
                        {"field_name": "currency", "field_description": "currency for rates", "mandatory": False, "object_type": "enum", "enum_values": ["USD", "EUR", "GBP", "CAD", "AUD", "INR", "SGD", "JPY"]}
                    ]
                },
                {
                    "name": "volume_discounts",
                    "description": "volume-based discount structure",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": True,
                    "fields": [
                        {"field_name": "threshold_amount", "field_description": "minimum amount for discount", "mandatory": False, "object_type": "numeric"},
                        {"field_name": "discount_percentage", "field_description": "discount percentage", "mandatory": False, "object_type": "numeric"},
                        {"field_name": "period", "field_description": "period for volume calculation", "mandatory": False, "object_type": "enum", "enum_values": ["Monthly", "Quarterly", "Annually", "Per SOW"]}
                    ]
                },
                {
                    "name": "payment_terms",
                    "description": "payment terms and conditions",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": False,
                    "fields": [
                        {"field_name": "payment_due_days", "field_description": "days for payment after invoice", "mandatory": False, "object_type": "numeric"},
                        {"field_name": "late_payment_interest", "field_description": "interest rate for late payments (percentage)", "mandatory": False, "object_type": "numeric"},
                        {"field_name": "late_payment_fees", "field_description": "fixed fees for late payments", "mandatory": False, "object_type": "numeric"},
                        {"field_name": "invoice_frequency", "field_description": "default invoicing frequency", "mandatory": False, "object_type": "enum", "enum_values": ["Weekly", "Bi-weekly", "Monthly", "Quarterly", "Upon Completion", "As per SOW"]}
                    ],
                    "children": [
                        {
                            "name": "accepted_payment_methods",
                            "description": "accepted payment methods",
                            "mandatory": False,
                            "object_type": "obj",
                            "is_list": True,
                            "fields": [
                                {"field_name": "value", "field_description": "payment method", "mandatory": False, "object_type": "enum", "enum_values": ["Wire Transfer", "ACH", "Check", "Credit Card", "Online Payment"]}
                            ]
                        }
                    ]
                },
                {
                    "name": "fees_and_charges",
                    "description": "additional fees and charges structure",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": False,
                    "fields": [
                        {"field_name": "administrative_fees", "field_description": "administrative or processing fees", "mandatory": False, "object_type": "numeric"},
                        {"field_name": "setup_fees", "field_description": "initial setup or onboarding fees", "mandatory": False, "object_type": "numeric"},
                        {"field_name": "cancellation_fees", "field_description": "fees for early cancellation", "mandatory": False, "object_type": "numeric"}
                    ]
                },
                {
                    "name": "discounts",
                    "description": "discount structures and conditions",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": True,
                    "fields": [
                        {"field_name": "discount_type", "field_description": "type of discount", "mandatory": False, "object_type": "enum", "enum_values": ["Volume", "Early Payment", "Promotional", "Long-term Contract", "Bundle"]},
                        {"field_name": "discount_value", "field_description": "discount percentage or amount", "mandatory": False, "object_type": "numeric"},
                        {"field_name": "discount_conditions", "field_description": "conditions for discount to apply", "mandatory": False, "object_type": "string"}
                    ]
                },
                {
                    "name": "surcharges",
                    "description": "surcharge structures",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": True,
                    "fields": [
                        {"field_name": "surcharge_type", "field_description": "type of surcharge", "mandatory": False, "object_type": "enum", "enum_values": ["Rush Service", "After Hours", "Weekend", "Holiday", "Remote Location", "Fuel", "Environmental"]},
                        {"field_name": "surcharge_rate", "field_description": "surcharge percentage or fixed amount", "mandatory": False, "object_type": "numeric"},
                        {"field_name": "surcharge_conditions", "field_description": "conditions when surcharge applies", "mandatory": False, "object_type": "string"}
                    ]
                },
                {
                    "name": "taxes",
                    "description": "tax provisions",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": False,
                    "fields": [
                        {"field_name": "tax_responsibility", "field_description": "party responsible for taxes", "mandatory": False, "object_type": "enum", "enum_values": ["Customer", "Provider", "Split", "As per law"]},
                        {"field_name": "tax_exemptions", "field_description": "any tax exemptions applicable", "mandatory": False, "object_type": "string"},
                        {"field_name": "withholding_tax", "field_description": "withholding tax provisions", "mandatory": False, "object_type": "string"}
                    ]
                },
                {
                    "name": "expense_reimbursement",
                    "description": "expense reimbursement policy",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": False,
                    "fields": [
                        {"field_name": "markup_percentage", "field_description": "markup on expenses if any", "mandatory": False, "object_type": "numeric"},
                        {"field_name": "approval_required", "field_description": "prior approval required?", "mandatory": False, "object_type": "boolean"},
                        {"field_name": "approval_threshold", "field_description": "amount above which approval required", "mandatory": False, "object_type": "numeric"}
                    ],
                    "children": [
                        {
                            "name": "reimbursable_expenses",
                            "description": "types of reimbursable expenses",
                            "mandatory": False,
                            "object_type": "obj",
                            "is_list": True,
                            "fields": [
                                {"field_name": "value", "field_description": "expense type", "mandatory": False, "object_type": "enum", "enum_values": ["Travel", "Accommodation", "Meals", "Transportation", "Materials", "Software Licenses"]}
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "name": "intellectual_property",
            "description": "intellectual property rights and ownership",
            "mandatory": False,
            "object_type": "obj",
            "is_list": False,
            "fields": [
                {"field_name": "ownership_model", "field_description": "default IP ownership model", "mandatory": False, "object_type": "enum", "enum_values": ["Work for Hire", "Provider Owned with License", "Joint Ownership", "Customer Owned", "As per SOW"]},
                {"field_name": "license_grants", "field_description": "specific license grants if applicable", "mandatory": False, "object_type": "string"},
                {"field_name": "deliverable_ownership", "field_description": "ownership of deliverables", "mandatory": False, "object_type": "enum", "enum_values": ["Customer", "Provider", "Joint", "As specified in SOW"]}
            ],
            "children": [
                {
                    "name": "pre_existing_ip",
                    "description": "handling of pre-existing IP",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": False,
                    "fields": [
                        {"field_name": "provider_retains_ownership", "field_description": "provider retains ownership of pre-existing IP", "mandatory": False, "object_type": "boolean"},
                        {"field_name": "license_to_customer", "field_description": "license granted to customer for pre-existing IP", "mandatory": False, "object_type": "enum", "enum_values": ["Perpetual", "Term-based", "Project-based", "None"]}
                    ]
                }
            ]
        },
        {
            "name": "confidentiality",
            "description": "confidentiality and non-disclosure terms",
            "mandatory": False,
            "object_type": "obj",
            "is_list": False,
            "fields": [
                {"field_name": "mutual_nda", "field_description": "whether NDA is mutual", "mandatory": False, "object_type": "boolean"},
                {"field_name": "confidentiality_period", "field_description": "period of confidentiality obligation in years", "mandatory": False, "object_type": "numeric"}
            ],
            "children": [
                {
                    "name": "exceptions",
                    "description": "standard exceptions to confidentiality",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": True,
                    "fields": [
                        {"field_name": "value", "field_description": "exception", "mandatory": False, "object_type": "enum", "enum_values": ["Publicly Available", "Independently Developed", "Previously Known", "Required by Law", "Third Party Disclosure"]}
                    ]
                }
            ]
        },
        {
            "name": "data_protection",
            "description": "data protection and privacy provisions",
            "mandatory": False,
            "object_type": "obj",
            "is_list": False,
            "fields": [
                {"field_name": "data_processing_agreement", "field_description": "whether separate DPA required", "mandatory": False, "object_type": "boolean"},
                {"field_name": "data_location_restrictions", "field_description": "restrictions on data storage locations", "mandatory": False, "object_type": "string"},
                {"field_name": "data_retention_period", "field_description": "data retention requirements", "mandatory": False, "object_type": "string"},
                {"field_name": "breach_notification_period", "field_description": "breach notification period in hours", "mandatory": False, "object_type": "numeric"}
            ],
            "children": [
                {
                    "name": "applicable_regulations",
                    "description": "applicable data protection regulations",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": True,
                    "fields": [
                        {"field_name": "value", "field_description": "regulation", "mandatory": False, "object_type": "enum", "enum_values": ["GDPR", "CCPA", "HIPAA", "PCI DSS", "SOC 2", "ISO 27001"]}
                    ]
                }
            ]
        },
        {
            "name": "compliance_requirements",
            "description": "regulatory compliance requirements",
            "mandatory": False,
            "object_type": "obj",
            "is_list": False,
            "fields": [
                {"field_name": "industry_specific", "field_description": "industry-specific compliance requirements", "mandatory": False, "object_type": "string"}
            ],
            "children": [
                {
                    "name": "regulatory_compliance",
                    "description": "specific regulatory compliance based on service type",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": True,
                    "fields": [
                        {"field_name": "regulation_type", "field_description": "type of regulation", "mandatory": False, "object_type": "enum", "enum_values": ["GDPR", "HIPAA", "SOX", "PCI DSS", "FERPA", "GLBA", "FCPA", "AML", "KYC", "ITAR", "EAR"]},
                        {"field_name": "compliance_requirements", "field_description": "specific compliance requirements", "mandatory": False, "object_type": "string"},
                        {"field_name": "audit_requirements", "field_description": "audit requirements for compliance", "mandatory": False, "object_type": "string"}
                    ]
                },
                {
                    "name": "import_export_compliance",
                    "description": "import/export law compliance",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": False,
                    "fields": [
                        {"field_name": "export_control_compliance", "field_description": "compliance with export control laws", "mandatory": False, "object_type": "boolean"},
                        {"field_name": "import_restrictions", "field_description": "any import restrictions applicable", "mandatory": False, "object_type": "string"},
                        {"field_name": "customs_duties_responsibility", "field_description": "party responsible for customs and duties", "mandatory": False, "object_type": "enum", "enum_values": ["Customer", "Provider", "As per Incoterms", "Not Applicable"]},
                        {"field_name": "prohibited_countries", "field_description": "countries where services/products cannot be provided", "mandatory": False, "object_type": "string"}
                    ]
                },
                {
                    "name": "hazmat_provisions",
                    "description": "hazardous materials handling provisions",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": False,
                    "fields": [
                        {"field_name": "hazmat_handling", "field_description": "whether agreement covers hazardous materials", "mandatory": False, "object_type": "boolean"},
                        {"field_name": "hazmat_compliance", "field_description": "compliance requirements for hazmat", "mandatory": False, "object_type": "string"},
                        {"field_name": "hazmat_certifications", "field_description": "required certifications for hazmat handling", "mandatory": False, "object_type": "string"},
                        {"field_name": "hazmat_liability", "field_description": "special liability provisions for hazmat", "mandatory": False, "object_type": "string"}
                    ]
                }
            ]
        },
        {
            "name": "liability_indemnification",
            "description": "liability limitations and indemnification",
            "mandatory": False,
            "object_type": "obj",
            "is_list": False,
            "fields": [
                {"field_name": "mutual_indemnification", "field_description": "whether indemnification is mutual", "mandatory": False, "object_type": "boolean"},
                {"field_name": "indemnification_scope", "field_description": "scope of indemnification", "mandatory": False, "object_type": "string"},
                {"field_name": "liability_allocation", "field_description": "how liability is allocated between parties", "mandatory": False, "object_type": "string"}
            ],
            "children": [
                {
                    "name": "indemnification_provisions",
                    "description": "detailed indemnification terms",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": False,
                    "fields": [
                        {"field_name": "customer_indemnifies", "field_description": "what customer indemnifies provider for", "mandatory": False, "object_type": "string"},
                        {"field_name": "provider_indemnifies", "field_description": "what provider indemnifies customer for", "mandatory": False, "object_type": "string"},
                        {"field_name": "defense_obligations", "field_description": "obligations to defend against claims", "mandatory": False, "object_type": "string"},
                        {"field_name": "notice_requirements", "field_description": "requirements for indemnification notice", "mandatory": False, "object_type": "string"}
                    ]
                },
                {
                    "name": "indemnification_exclusions",
                    "description": "exclusions from indemnification",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": True,
                    "fields": [
                        {"field_name": "value", "field_description": "indemnification exclusion", "mandatory": False, "object_type": "string"}
                    ]
                },
                {
                    "name": "liability_cap",
                    "description": "limitation of liability",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": False,
                    "fields": [
                        {"field_name": "cap_type", "field_description": "type of liability cap", "mandatory": False, "object_type": "enum", "enum_values": ["Fixed Amount", "Multiple of Fees", "Annual Fees", "Uncapped", "Per Incident"]},
                        {"field_name": "cap_amount", "field_description": "cap amount if fixed", "mandatory": False, "object_type": "numeric"},
                        {"field_name": "cap_multiplier", "field_description": "multiplier if based on fees", "mandatory": False, "object_type": "numeric"},
                        {"field_name": "aggregate_cap", "field_description": "aggregate liability cap", "mandatory": False, "object_type": "numeric"}
                    ]
                },
                {
                    "name": "liability_exclusions",
                    "description": "exclusions from liability limitation",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": True,
                    "fields": [
                        {"field_name": "value", "field_description": "exclusion", "mandatory": False, "object_type": "enum", "enum_values": ["Gross Negligence", "Breach of Confidentiality", "IP Infringement", "Data Protection Breach", "Indemnification", "Willful Misconduct", "Third Party Claims"]}
                    ]
                }
            ]
        },
        {
            "name": "warranties",
            "description": "warranties and service levels",
            "mandatory": False,
            "object_type": "obj",
            "is_list": False,
            "fields": [
                {"field_name": "service_warranty_period", "field_description": "warranty period for services in days", "mandatory": False, "object_type": "numeric"},
                {"field_name": "warranty_disclaimers", "field_description": "warranty disclaimers", "mandatory": False, "object_type": "string"}
            ],
            "children": [
                {
                    "name": "performance_standards",
                    "description": "performance standards and SLAs",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": False,
                    "fields": [
                        {"field_name": "availability_sla", "field_description": "availability SLA percentage", "mandatory": False, "object_type": "numeric"},
                        {"field_name": "response_time_sla", "field_description": "response time SLA in hours", "mandatory": False, "object_type": "numeric"},
                        {"field_name": "resolution_time_sla", "field_description": "resolution time SLA in hours", "mandatory": False, "object_type": "numeric"}
                    ]
                }
            ]
        },
        {
            "name": "termination",
            "description": "termination provisions",
            "mandatory": False,
            "object_type": "obj",
            "is_list": False,
            "fields": [
                {"field_name": "term", "field_description": "term of the agreement", "mandatory": False, "object_type": "string"},
                {"field_name": "termination_for_convenience", "field_description": "whether either party can terminate for convenience", "mandatory": False, "object_type": "boolean"},
                {"field_name": "convenience_notice_period", "field_description": "notice period for convenience termination in days", "mandatory": False, "object_type": "numeric"},
                {"field_name": "cure_period", "field_description": "cure period for breaches in days", "mandatory": False, "object_type": "numeric"}
            ],
            "children": [
                {
                    "name": "termination_for_cause",
                    "description": "grounds for termination for cause",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": True,
                    "fields": [
                        {"field_name": "value", "field_description": "cause", "mandatory": False, "object_type": "enum", "enum_values": ["Material Breach", "Insolvency", "Change of Control", "Illegal Activity", "Breach of Confidentiality"]}
                    ]
                },
                {
                    "name": "termination_exclusions",
                    "description": "exclusions or limitations on termination rights",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": True,
                    "fields": [
                        {"field_name": "value", "field_description": "termination exclusion or limitation", "mandatory": False, "object_type": "string"}
                    ]
                },
                {
                    "name": "survival_clauses",
                    "description": "clauses that survive termination",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": True,
                    "fields": [
                        {"field_name": "value", "field_description": "surviving clause", "mandatory": False, "object_type": "enum", "enum_values": ["Confidentiality", "Intellectual Property", "Indemnification", "Limitation of Liability", "Payment Obligations", "Termination"]}
                    ]
                }
            ]
        },
        {
            "name": "dispute_resolution",
            "description": "dispute resolution procedures",
            "mandatory": False,
            "object_type": "obj",
            "is_list": False,
            "fields": [
                {"field_name": "escalation_process", "field_description": "internal escalation before formal dispute", "mandatory": False, "object_type": "boolean"},
                {"field_name": "escalation_period", "field_description": "escalation period in days", "mandatory": False, "object_type": "numeric"},
                {"field_name": "dispute_resolution_method", "field_description": "primary dispute resolution method", "mandatory": False, "object_type": "enum", "enum_values": ["Litigation", "Arbitration", "Mediation then Arbitration", "Mediation then Litigation"]},
                {"field_name": "arbitration_rules", "field_description": "arbitration rules if applicable", "mandatory": False, "object_type": "enum", "enum_values": ["AAA", "JAMS", "ICC", "UNCITRAL", "Other"]},
                {"field_name": "venue", "field_description": "venue for disputes", "mandatory": False, "object_type": "string"},
                {"field_name": "attorneys_fees", "field_description": "recovery of attorneys fees", "mandatory": False, "object_type": "enum", "enum_values": ["Each Party Bears Own", "Prevailing Party", "As Determined by Court/Arbitrator"]}
            ]
        },
        {
            "name": "insurance",
            "description": "insurance requirements",
            "mandatory": False,
            "object_type": "obj",
            "is_list": False,
            "fields": [
                {"field_name": "workers_compensation", "field_description": "workers compensation insurance", "mandatory": False, "object_type": "boolean"}
            ],
            "children": [
                {
                    "name": "general_liability",
                    "description": "general liability insurance requirement",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": False,
                    "fields": [
                        {"field_name": "required", "field_description": "whether required", "mandatory": False, "object_type": "boolean"},
                        {"field_name": "minimum_coverage", "field_description": "minimum coverage amount", "mandatory": False, "object_type": "numeric"}
                    ]
                },
                {
                    "name": "professional_liability",
                    "description": "professional liability/E&O insurance",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": False,
                    "fields": [
                        {"field_name": "required", "field_description": "whether required", "mandatory": False, "object_type": "boolean"},
                        {"field_name": "minimum_coverage", "field_description": "minimum coverage amount", "mandatory": False, "object_type": "numeric"}
                    ]
                },
                {
                    "name": "cyber_liability",
                    "description": "cyber liability insurance",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": False,
                    "fields": [
                        {"field_name": "required", "field_description": "whether required", "mandatory": False, "object_type": "boolean"},
                        {"field_name": "minimum_coverage", "field_description": "minimum coverage amount", "mandatory": False, "object_type": "numeric"}
                    ]
                }
            ]
        },
        {
            "name": "general_provisions",
            "description": "general contractual provisions",
            "mandatory": False,
            "object_type": "obj",
            "is_list": False,
            "fields": [
                {"field_name": "entire_agreement", "field_description": "entire agreement clause", "mandatory": False, "object_type": "boolean"},
                {"field_name": "amendment_process", "field_description": "how agreement can be amended", "mandatory": False, "object_type": "enum", "enum_values": ["Written Agreement Only", "Email Confirmation", "As per SOW"]},
                {"field_name": "force_majeure", "field_description": "force majeure provisions", "mandatory": False, "object_type": "boolean"},
                {"field_name": "severability", "field_description": "severability clause", "mandatory": False, "object_type": "boolean"},
                {"field_name": "waiver_provisions", "field_description": "waiver provisions", "mandatory": False, "object_type": "string"}
            ],
            "children": [
                {
                    "name": "assignment_rights",
                    "description": "assignment and transfer rights",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": False,
                    "fields": [
                        {"field_name": "customer_assignment", "field_description": "customer's right to assign", "mandatory": False, "object_type": "enum", "enum_values": ["Freely Assignable", "With Consent", "Not Assignable", "To Affiliates Only"]},
                        {"field_name": "provider_assignment", "field_description": "provider's right to assign", "mandatory": False, "object_type": "enum", "enum_values": ["Freely Assignable", "With Consent", "Not Assignable", "To Affiliates Only"]}
                    ]
                },
                {
                    "name": "notices",
                    "description": "notice provisions",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": False,
                    "fields": [
                        {"field_name": "notice_addresses", "field_description": "addresses for notices", "mandatory": False, "object_type": "string"}
                    ],
                    "children": [
                        {
                            "name": "notice_methods",
                            "description": "acceptable notice methods",
                            "mandatory": False,
                            "object_type": "obj",
                            "is_list": True,
                            "fields": [
                                {"field_name": "value", "field_description": "method", "mandatory": False, "object_type": "enum", "enum_values": ["Email", "Certified Mail", "Courier", "Personal Delivery"]}
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "name": "related_documents",
            "description": "related agreements and documents",
            "mandatory": False,
            "object_type": "obj",
            "is_list": False,
            "fields": [],
            "children": [
                {
                    "name": "superseded_agreements",
                    "description": "agreements superseded by this MSA",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": True,
                    "fields": [
                        {"field_name": "agreement_name", "field_description": "name of superseded agreement", "mandatory": False, "object_type": "string"},
                        {"field_name": "agreement_date", "field_description": "date of superseded agreement", "mandatory": False, "object_type": "date"}
                    ]
                },
                {
                    "name": "incorporated_documents",
                    "description": "documents incorporated by reference",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": True,
                    "fields": [
                        {"field_name": "document_name", "field_description": "name of incorporated document", "mandatory": False, "object_type": "string"},
                        {"field_name": "document_version", "field_description": "version of incorporated document", "mandatory": False, "object_type": "string"},
                        {"field_name": "document_url", "field_description": "URL or location of document", "mandatory": False, "object_type": "string"}
                    ]
                },
                {
                    "name": "exhibits",
                    "description": "exhibits attached to MSA",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": True,
                    "fields": [
                        {"field_name": "exhibit_id", "field_description": "exhibit identifier", "mandatory": False, "object_type": "string"},
                        {"field_name": "exhibit_title", "field_description": "title of exhibit", "mandatory": False, "object_type": "string"},
                        {"field_name": "exhibit_description", "field_description": "description of exhibit content", "mandatory": False, "object_type": "string"}
                    ]
                }
            ]
        },
        {
            "name": "execution_details",
            "description": "execution and signature details",
            "mandatory": True,
            "object_type": "obj",
            "is_list": False,
            "fields": [
                {"field_name": "execution_date", "field_description": "date of execution", "mandatory": True, "object_type": "date"},
                {"field_name": "counterparts", "field_description": "whether can be executed in counterparts", "mandatory": False, "object_type": "boolean"},
                {"field_name": "electronic_signatures", "field_description": "whether electronic signatures accepted", "mandatory": False, "object_type": "boolean"}
            ],
            "children": [
                {
                    "name": "customer_execution",
                    "description": "customer execution details",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": False,
                    "fields": [
                        {"field_name": "signatory_name", "field_description": "name of signatory", "mandatory": False, "object_type": "string"},
                        {"field_name": "signatory_title", "field_description": "title of signatory", "mandatory": False, "object_type": "string"},
                        {"field_name": "signature_date", "field_description": "date of signature", "mandatory": False, "object_type": "date"},
                        {"field_name": "witness_required", "field_description": "whether witness required", "mandatory": False, "object_type": "boolean"}
                    ]
                },
                {
                    "name": "provider_execution",
                    "description": "provider execution details",
                    "mandatory": False,
                    "object_type": "obj",
                    "is_list": False,
                    "fields": [
                        {"field_name": "signatory_name", "field_description": "name of signatory", "mandatory": False, "object_type": "string"},
                        {"field_name": "signatory_title", "field_description": "title of signatory", "mandatory": False, "object_type": "string"},
                        {"field_name": "signature_date", "field_description": "date of signature", "mandatory": False, "object_type": "date"},
                        {"field_name": "witness_required", "field_description": "whether witness required", "mandatory": False, "object_type": "boolean"}
                    ]
                }
            ]
        }
    ]
}


def generate_msa_extraction_prompt(schema: Dict[str, Any], is_chunk: bool = False, chunk_number: Optional[int] = None, total_chunks: Optional[int] = None) -> str:
    """Generate a detailed prompt for extracting MSA data according to the schema."""
    
    def build_schema_description(obj: Dict[str, Any], indent: int = 0) -> List[str]:
        """Recursively build a description of the schema."""
        prefix = "  " * indent
        lines = []
        
        name = obj.get("name", "")
        desc = obj.get("description", "")
        mandatory = obj.get("mandatory", False)
        obj_type = obj.get("object_type", "")
        is_list = obj.get("is_list", False)
        
        lines.append(f"{prefix}- {name} ({'MANDATORY' if mandatory else 'OPTIONAL'})")
        if desc:
            lines.append(f"{prefix}  Description: {desc}")
        if is_list:
            lines.append(f"{prefix}  Type: List of {obj_type}")
        else:
            lines.append(f"{prefix}  Type: {obj_type}")
        
        # Add fields
        fields = obj.get("fields", [])
        if fields:
            lines.append(f"{prefix}  Fields:")
            for field in fields:
                field_name = field.get("field_name", "")
                field_desc = field.get("field_description", "")
                field_mandatory = field.get("mandatory", False)
                field_type = field.get("object_type", "")
                enum_values = field.get("enum_values", [])
                
                mandatory_marker = " (MANDATORY)" if field_mandatory else ""
                lines.append(f"{prefix}    - {field_name}: {field_type}{mandatory_marker}")
                if field_desc:
                    lines.append(f"{prefix}      Description: {field_desc}")
                if enum_values:
                    lines.append(f"{prefix}      Allowed values: {', '.join(enum_values)}")
        
        # Add children
        children = obj.get("children", [])
        if children:
            lines.append(f"{prefix}  Children:")
            for child in children:
                lines.extend(build_schema_description(child, indent + 1))
        
        return lines
    
    schema_lines = build_schema_description(schema)
    schema_text = "\n".join(schema_lines)
    
    # Chunk-aware instructions
    chunk_context = ""
    if is_chunk:
        chunk_context = f"""
⚠️  IMPORTANT: This is CHUNK {chunk_number} of {total_chunks} from a larger MSA document.
- Extract ONLY the fields that are present in THIS chunk
- If a field is not mentioned in this chunk, use null or omit it
- You will extract fields from other chunks separately, so focus only on what's in this section
- Common fields that might appear in any chunk: msa_id, effective_date, executed_date, governing_law, nature_of_services
- Party information (customer/provider) might appear in early chunks
- Commercial terms, IP, liability sections typically appear in middle/later chunks
"""
    
    prompt = f"""You are an expert legal document parser specializing in Master Service Agreements (MSAs). Your task is to extract structured information from the MSA document according to the following schema.
{chunk_context}
SCHEMA STRUCTURE:
{schema_text}

INSTRUCTIONS:
1. Extract ALL information from the document that matches the schema fields
2. For mandatory fields, you MUST extract the value if present. If a mandatory field is not found in this section, use null
3. For optional fields, only include them if the information is present in the document
4. For enum fields, use EXACTLY one of the allowed values listed, or null if not found. IMPORTANT: If you see "None" or "N/A" for pre-existing IP license, use null instead (it's not in the enum list)
5. For boolean fields, use true/false/null
6. For numeric fields, extract the numeric value (integer or float)
7. For date fields, extract dates in ISO format (YYYY-MM-DD) or as found in the document
8. For string fields, extract the exact text from the document
9. For list fields (is_list: true), create an array of objects
10. Maintain the exact nested structure as defined in the schema
11. Do NOT add fields that are not in the schema
12. Do NOT modify field names
13. If a section is not present in this chunk, use null for its fields or omit it entirely (unless it's mandatory)

CRITICAL SECTIONS TO EXTRACT (if present in document):
- compliance_requirements: Look for regulatory compliance, import/export compliance, hazmat provisions
- liability_indemnification: Extract detailed structure including indemnification_provisions, liability_cap, liability_exclusions
- warranties: Extract service warranties, performance standards, SLAs (availability, response time, resolution time)
- dispute_resolution: Extract escalation process, arbitration rules, venue, attorneys fees
- commercial_terms: Extract rate_cards, volume_discounts, payment_terms (including accepted_payment_methods), fees_and_charges, discounts, surcharges, taxes, expense_reimbursement
- intellectual_property: Extract ownership_model, license_grants, deliverable_ownership, pre_existing_ip (use null for license_to_customer if not applicable, NOT "None")

OUTPUT FORMAT:
Return ONLY valid JSON that matches the schema structure. The JSON should be properly formatted and parseable.

IMPORTANT:
- Extract information accurately from the document text
- Do not infer or assume values not explicitly stated
- For nested objects, maintain the exact structure
- For lists, create arrays even if there's only one item
- Use null for missing optional fields
- Use empty strings "" for missing optional string fields if that's more appropriate than null
- Return a complete JSON structure matching the schema, even if most fields are null (this allows merging with other chunks)

Now, parse the following MSA document section and extract the structured data:"""
    
    return prompt


class MSAParser:
    """Parser for extracting structured MSA data from documents."""
    
    def __init__(self, llm: ChatOpenAI):
        """
        Initialize the MSA Parser.
        
        Args:
            llm: LangChain LLM instance for extraction
        """
        self.llm = llm
        self.schema = MSA_SCHEMA
        # Base prompt template (will be customized per chunk)
        self.base_prompt_template = generate_msa_extraction_prompt(self.schema, is_chunk=False)
    
    def parse(self, document_text: str, max_chunk_size: int = 100000) -> Dict[str, Any]:
        """
        Parse MSA document text and extract structured data.
        
        Args:
            document_text: Full text content of the MSA document
            max_chunk_size: Maximum total characters per request (prompt + document)
            
        Returns:
            Dictionary containing structured MSA data matching the schema
        """
        start_time = time.time()
        logger.info("=" * 80)
        logger.info("Starting MSA parsing process")
        logger.info("=" * 80)
        
        text_length = len(document_text)
        # Use base prompt length for calculations (chunk prompts will be similar size)
        prompt_length = len(self.base_prompt_template)
        
        # Calculate effective max document size per request
        # Leave room for prompt + response overhead (roughly 1.5x prompt size for safety)
        # Ensure we have at least some room for the document
        overhead = int(prompt_length * 1.5)
        effective_max_doc_size = max_chunk_size - overhead
        
        # If prompt is too large, we need to increase max_chunk_size or reduce prompt
        if effective_max_doc_size <= 0:
            logger.warning(f"⚠️  Prompt ({prompt_length:,} chars) is larger than max_chunk_size ({max_chunk_size:,} chars)")
            logger.warning(f"   Increasing max_chunk_size to accommodate prompt...")
            # Set max_chunk_size to at least 2x prompt size to leave room for document
            max_chunk_size = max(max_chunk_size, int(prompt_length * 2.5))
            effective_max_doc_size = max_chunk_size - overhead
            logger.info(f"   Adjusted max_chunk_size to {max_chunk_size:,} chars")
            logger.info(f"   Effective max document size: {effective_max_doc_size:,} chars")
        
        logger.info(f"📊 Document Statistics:")
        logger.info(f"   - Document length: {text_length:,} characters")
        logger.info(f"   - Prompt length: {prompt_length:,} characters")
        logger.info(f"   - Max chunk size: {max_chunk_size:,} characters")
        logger.info(f"   - Effective max document size per request: {effective_max_doc_size:,} characters")
        
        # Safety limit: Even if document "fits", chunk if total request would be too large
        # The Qwen server has a timeout, so we need to keep requests under ~50k chars total
        safe_total_request_size = 50000  # Conservative limit to avoid gateway timeouts
        total_request_size = prompt_length + text_length
        logger.info(f"   - Total request size (prompt + document): {total_request_size:,} characters")
        logger.info(f"   - Safe request size limit: {safe_total_request_size:,} characters")
        
        # If document fits in one request AND total size is safe, process it directly
        if text_length <= effective_max_doc_size and total_request_size <= safe_total_request_size:
            logger.info("📄 Document fits in single request and is within safe size limit, processing directly...")
            result = self._parse_single_chunk(document_text, is_chunk=False)
            # Fix enum values
            result = self._fix_enum_values(result)
            # Validate structure
            self._validate_structure(result)
            elapsed = time.time() - start_time
            logger.info("=" * 80)
            logger.info(f"✅ MSA extraction completed successfully in {elapsed:.2f} seconds")
            logger.info("=" * 80)
            return result
        
        # Force chunking if total request would be too large (even if doc "fits")
        if total_request_size > safe_total_request_size:
            logger.info(f"⚠️  Total request size ({total_request_size:,} chars) exceeds safe limit ({safe_total_request_size:,} chars)")
            logger.info(f"   Forcing chunking to avoid gateway timeout...")
            # Adjust effective_max_doc_size to ensure chunks stay under safe limit
            effective_max_doc_size = min(effective_max_doc_size, safe_total_request_size - prompt_length)
            logger.info(f"   Adjusted effective max document size to: {effective_max_doc_size:,} chars")
        
        # Otherwise, chunk the document and merge results
        logger.info(f"📦 Document too large ({text_length:,} chars), chunking into smaller pieces...")
        chunk_start = time.time()
        chunks = self._chunk_document(document_text, effective_max_doc_size)
        chunk_time = time.time() - chunk_start
        logger.info(f"✅ Split document into {len(chunks)} chunks in {chunk_time:.2f} seconds")
        logger.info(f"   Chunk sizes: {[len(c) for c in chunks]}")
        
        # Parse each chunk
        all_results = []
        total_llm_time = 0.0
        for i, chunk in enumerate(chunks, 1):
            chunk_start_time = time.time()
            logger.info("-" * 80)
            logger.info(f"🔄 Processing chunk {i}/{len(chunks)} ({len(chunk):,} characters)")
            logger.info(f"   Started at: {time.strftime('%H:%M:%S')}")
            try:
                # Use chunk-aware prompt
                chunk_result = self._parse_single_chunk(chunk, is_chunk=True, chunk_number=i, total_chunks=len(chunks))
                chunk_elapsed = time.time() - chunk_start_time
                total_llm_time += chunk_elapsed
                logger.info(f"   ✅ Chunk {i} completed in {chunk_elapsed:.2f} seconds")
                logger.info(f"   Extracted {len(chunk_result)} top-level fields")
                all_results.append(chunk_result)
            except Exception as e:
                chunk_elapsed = time.time() - chunk_start_time
                logger.error(f"   ❌ Error processing chunk {i} after {chunk_elapsed:.2f} seconds: {str(e)}")
                # Continue with other chunks, but log the error
                continue
        
        logger.info("-" * 80)
        logger.info(f"📊 Chunk Processing Summary:")
        logger.info(f"   - Total chunks processed: {len(all_results)}/{len(chunks)}")
        logger.info(f"   - Total LLM processing time: {total_llm_time:.2f} seconds")
        logger.info(f"   - Average time per chunk: {total_llm_time/len(all_results):.2f} seconds" if all_results else "   - No chunks processed")
        
        # Merge results from all chunks
        if not all_results:
            raise ValueError("Failed to parse any chunks of the document")
        
        logger.info("-" * 80)
        logger.info("🔀 Merging results from all chunks...")
        merge_start = time.time()
        merged_result = self._merge_chunk_results(all_results)
        merge_time = time.time() - merge_start
        logger.info(f"✅ Merged {len(all_results)} chunk results in {merge_time:.2f} seconds")
        
        # Fix enum values and other data issues
        logger.info("-" * 80)
        logger.info("🔧 Post-processing: fixing enum values and data issues...")
        postprocess_start = time.time()
        merged_result = self._fix_enum_values(merged_result)
        postprocess_time = time.time() - postprocess_start
        logger.info(f"✅ Post-processing completed in {postprocess_time:.3f} seconds")
        
        # Validate structure
        logger.info("-" * 80)
        logger.info("✔️  Validating structure...")
        validation_start = time.time()
        self._validate_structure(merged_result)
        validation_time = time.time() - validation_start
        logger.info(f"✅ Structure validation completed in {validation_time:.2f} seconds")
        
        total_elapsed = time.time() - start_time
        logger.info("=" * 80)
        logger.info(f"✅ MSA extraction completed successfully!")
        logger.info(f"   Total time: {total_elapsed:.2f} seconds")
        logger.info(f"   Breakdown:")
        logger.info(f"     - Chunking: {chunk_time:.2f}s ({chunk_time/total_elapsed*100:.1f}%)")
        logger.info(f"     - LLM processing: {total_llm_time:.2f}s ({total_llm_time/total_elapsed*100:.1f}%)")
        logger.info(f"     - Merging: {merge_time:.2f}s ({merge_time/total_elapsed*100:.1f}%)")
        logger.info(f"     - Post-processing: {postprocess_time:.3f}s ({postprocess_time/total_elapsed*100:.1f}%)")
        logger.info(f"     - Validation: {validation_time:.2f}s ({validation_time/total_elapsed*100:.1f}%)")
        logger.info("=" * 80)
        return merged_result
    
    def _parse_single_chunk(self, document_text: str, is_chunk: bool = False, chunk_number: Optional[int] = None, total_chunks: Optional[int] = None) -> Dict[str, Any]:
        """Parse a single chunk of the document."""
        # Generate chunk-aware prompt if needed
        if is_chunk and chunk_number and total_chunks:
            extraction_prompt = generate_msa_extraction_prompt(self.schema, is_chunk=True, chunk_number=chunk_number, total_chunks=total_chunks)
        else:
            extraction_prompt = self.base_prompt_template
        
        # Combine prompt with document text
        prompt_start = time.time()
        full_prompt = f"{extraction_prompt}\n\n{document_text}"
        prompt_prep_time = time.time() - prompt_start
        logger.info(f"   📝 Prepared prompt in {prompt_prep_time:.3f}s (total prompt size: {len(full_prompt):,} chars)")
        if is_chunk:
            logger.info(f"   📌 Using chunk-aware prompt (chunk {chunk_number}/{total_chunks})")
        
        # Invoke LLM
        llm_start = time.time()
        logger.info(f"   🤖 Invoking LLM (document: {len(document_text):,} chars, prompt: {len(extraction_prompt):,} chars)...")
        try:
            response = self.llm.invoke(full_prompt)
            llm_time = time.time() - llm_start
            logger.info(f"   ✅ LLM responded in {llm_time:.2f} seconds")
        except Exception as e:
            llm_time = time.time() - llm_start
            logger.error(f"   ❌ LLM invocation failed after {llm_time:.2f} seconds: {str(e)}")
            raise
        
        # Extract response text
        extract_start = time.time()
        if hasattr(response, 'content'):
            response_text = str(response.content)
        else:
            response_text = str(response)
        extract_time = time.time() - extract_start
        logger.info(f"   📥 Extracted response text in {extract_time:.3f}s (response length: {len(response_text):,} chars)")
        
        # Extract JSON from response
        json_start = time.time()
        logger.info(f"   🔍 Extracting JSON from response...")
        parsed_data = self._extract_json(response_text)
        json_time = time.time() - json_start
        logger.info(f"   ✅ JSON extraction completed in {json_time:.3f}s")
        
        total_chunk_time = time.time() - prompt_start
        logger.info(f"   ⏱️  Total chunk processing time: {total_chunk_time:.2f}s")
        
        return parsed_data
    
    def _chunk_document(self, text: str, max_chunk_size: int) -> list:
        """Split document into chunks at section boundaries."""
        if len(text) <= max_chunk_size:
            return [text]
        
        logger.info(f"   🔍 Finding section boundaries...")
        find_start = time.time()
        chunks = []
        # Try to split by common section markers
        section_patterns = [
            r'\n\s*\d+\.\d+',  # 1.1, 2.3, etc.
            r'\n\s*\d+\([a-z]\)',  # 1(a), 2(b), etc.
            r'\n\s*SECTION\s+\d+',
            r'\n\s*Article\s+\d+',
            r'\n\s*Clause\s+\d+',
            r'\n\s*[A-Z][A-Z\s]+\n',  # All caps headings
        ]
        
        # Find all potential split points
        split_points = [0]
        for pattern in section_patterns:
            for match in re.finditer(pattern, text):
                pos = match.start()
                # Only add split points that are reasonably spaced
                if pos > split_points[-1] + max_chunk_size // 3:
                    split_points.append(pos)
        
        # Add end point
        split_points.append(len(text))
        
        # Sort and deduplicate split points
        split_points = sorted(set(split_points))
        find_time = time.time() - find_start
        logger.info(f"   ✅ Found {len(split_points)} potential split points in {find_time:.3f}s")
        
        # Create chunks, ensuring they don't exceed max size
        for i in range(len(split_points) - 1):
            start = split_points[i]
            end = split_points[i + 1]
            
            chunk = text[start:end]
            
            # If chunk exceeds max size, split it further by paragraphs
            while len(chunk) > max_chunk_size:
                # Find a good split point (preferably at paragraph boundary)
                split_at = max_chunk_size
                # Try to find paragraph boundary near max_chunk_size (within 40% of max)
                para_boundary = chunk.rfind('\n\n', max_chunk_size - int(max_chunk_size * 0.4), max_chunk_size)
                if para_boundary > max_chunk_size * 0.6:
                    split_at = para_boundary + 2
                else:
                    # Fall back to line break (within 30% of max)
                    line_break = chunk.rfind('\n', max_chunk_size - int(max_chunk_size * 0.3), max_chunk_size)
                    if line_break > max_chunk_size * 0.7:
                        split_at = line_break + 1
                    else:
                        # Last resort: split at max_chunk_size
                        split_at = max_chunk_size
                
                chunks.append(chunk[:split_at].strip())
                chunk = chunk[split_at:].strip()
            
            if chunk:
                chunks.append(chunk.strip())
        
        # Final safety check: ensure no chunk exceeds max size
        final_chunks = []
        for chunk in chunks:
            if len(chunk) > max_chunk_size:
                # Force split at max_chunk_size
                while len(chunk) > max_chunk_size:
                    final_chunks.append(chunk[:max_chunk_size].strip())
                    chunk = chunk[max_chunk_size:].strip()
                if chunk:
                    final_chunks.append(chunk.strip())
            else:
                final_chunks.append(chunk)
        
        return [c for c in final_chunks if c]  # Remove empty chunks
    
    def _merge_chunk_results(self, chunk_results: list) -> Dict[str, Any]:
        """Merge results from multiple chunks into a single result."""
        if len(chunk_results) == 1:
            logger.info(f"   ℹ️  Only one chunk result, skipping merge")
            return chunk_results[0]
        
        logger.info(f"   🔀 Merging {len(chunk_results)} chunk results...")
        # Start with the first result as base
        merged = chunk_results[0].copy()
        
        # Merge subsequent results, prioritizing non-null values
        for i, result in enumerate(chunk_results[1:], 2):
            merge_start = time.time()
            merged = self._deep_merge(merged, result)
            merge_time = time.time() - merge_start
            logger.info(f"   ✅ Merged chunk {i} in {merge_time:.3f}s")
        
        logger.info(f"   ✅ Merge complete. Final result has {len(merged)} top-level fields")
        return merged
    
    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries, preferring non-null values from update."""
        result = base.copy()
        
        for key, value in update.items():
            if key not in result:
                # New key, add it (even if null, we want the structure)
                result[key] = value
            elif result[key] is None and value is not None:
                # Base has null, update has value - use update
                result[key] = value
            elif value is None and result[key] is not None:
                # Update has null, base has value - keep base
                pass  # result[key] already has the value
            elif isinstance(value, dict) and isinstance(result[key], dict):
                # Both are dicts, merge recursively
                result[key] = self._deep_merge(result[key], value)
            elif isinstance(value, list) and isinstance(result[key], list):
                # Both are lists, merge them (avoid duplicates)
                merged_list = result[key] + [item for item in value if item not in result[key]]
                result[key] = merged_list
            elif value is not None and (result[key] is None or result[key] == ""):
                # Update has non-null value and base has null/empty, use update
                result[key] = value
            elif isinstance(value, str) and value.strip() and (not result[key] or not result[key].strip()):
                # Update has non-empty string and base is empty, use update
                result[key] = value
        
        return result
    
    def _fix_enum_values(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Fix invalid enum values in the extracted data."""
        # Fix pre-existing IP license enum
        ip_section = data.get("intellectual_property", {})
        if isinstance(ip_section, dict):
            pre_existing_ip = ip_section.get("pre_existing_ip", {})
            if isinstance(pre_existing_ip, dict):
                license_value = pre_existing_ip.get("license_to_customer")
                if license_value == "None" or license_value == "N/A" or license_value == "none":
                    logger.info("🔧 Fixing invalid enum value: license_to_customer 'None' -> null")
                    pre_existing_ip["license_to_customer"] = None
        
        return data
    
    def _extract_json(self, response_text: str) -> Dict[str, Any]:
        """Extract JSON from LLM response text."""
        # Try to find JSON block
        # Look for JSON code blocks
        json_block_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', response_text, re.DOTALL)
        if json_block_match:
            json_str = json_block_match.group(1)
        else:
            # Look for JSON object directly
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                raise ValueError("No JSON found in LLM response")
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            logger.error(f"JSON string: {json_str[:500]}")
            raise ValueError(f"Invalid JSON in response: {str(e)}")
    
    def _validate_structure(self, data: Dict[str, Any]) -> None:
        """Comprehensive validation of extracted data structure."""
        # Check for top-level required fields
        required_top_fields = ["msa_id", "effective_date", "executed_date", "nature_of_services", "governing_law"]
        for field in required_top_fields:
            if field not in data:
                logger.warning(f"⚠️  Missing required top-level field: {field}")
        
        # Check for required child objects
        if "customer" not in data:
            logger.warning("⚠️  Missing required child object: customer")
        elif "authorized_signatory" not in data.get("customer", {}):
            logger.warning("⚠️  Missing required customer.authorized_signatory")
        
        if "provider" not in data:
            logger.warning("⚠️  Missing required child object: provider")
        elif "authorized_signatory" not in data.get("provider", {}):
            logger.warning("⚠️  Missing required provider.authorized_signatory")
        
        if "services_scope" not in data:
            logger.warning("⚠️  Missing required child object: services_scope")
        
        if "execution_details" not in data:
            logger.warning("⚠️  Missing required child object: execution_details")
        
        # Check for important optional sections that are commonly present
        important_sections = {
            "compliance_requirements": "Compliance Requirements (regulatory_compliance, import_export_compliance, hazmat_provisions)",
            "liability_indemnification": "Liability & Indemnification (detailed structure)",
            "warranties": "Warranties (service warranties + SLAs)",
            "dispute_resolution": "Dispute Resolution (escalation, arbitration rules, attorneys fees)",
            "commercial_terms": "Commercial Terms (rate_cards, volume_discounts, payment_terms, etc.)"
        }
        
        for section_key, section_name in important_sections.items():
            if section_key not in data or data.get(section_key) is None:
                logger.warning(f"⚠️  Missing or null: {section_name}")
            else:
                # Check nested structures
                section_data = data.get(section_key, {})
                if section_key == "compliance_requirements":
                    if not section_data.get("regulatory_compliance") and not section_data.get("import_export_compliance"):
                        logger.warning(f"⚠️  {section_name} exists but missing regulatory_compliance and import_export_compliance")
                
                elif section_key == "liability_indemnification":
                    if not section_data.get("indemnification_provisions") and not section_data.get("liability_cap"):
                        logger.warning(f"⚠️  {section_name} exists but missing detailed indemnification_provisions or liability_cap")
                
                elif section_key == "warranties":
                    if not section_data.get("performance_standards"):
                        logger.warning(f"⚠️  {section_name} exists but missing performance_standards/SLAs")
                
                elif section_key == "dispute_resolution":
                    if not section_data.get("dispute_resolution_method") and not section_data.get("arbitration_rules"):
                        logger.warning(f"⚠️  {section_name} exists but missing dispute_resolution_method or arbitration_rules")
                
                elif section_key == "commercial_terms":
                    payment_terms = section_data.get("payment_terms", {})
                    if payment_terms and not payment_terms.get("accepted_payment_methods"):
                        logger.warning(f"⚠️  {section_name} has payment_terms but missing accepted_payment_methods")
                    if not section_data.get("rate_cards") and not section_data.get("volume_discounts"):
                        logger.warning(f"⚠️  {section_name} exists but missing rate_cards or volume_discounts")
        
        # Check for enum value issues
        ip_section = data.get("intellectual_property", {})
        pre_existing_ip = ip_section.get("pre_existing_ip", {}) if isinstance(ip_section, dict) else {}
        if isinstance(pre_existing_ip, dict):
            license_value = pre_existing_ip.get("license_to_customer")
            if license_value == "None" or license_value == "N/A":
                logger.warning("⚠️  Invalid enum value for intellectual_property.pre_existing_ip.license_to_customer: 'None' or 'N/A'. Should be null or one of: Perpetual, Term-based, Project-based, None")
        
        logger.info("Structure validation completed")

