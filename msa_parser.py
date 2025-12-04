#!/usr/bin/env python3
"""
MSA (Master Service Agreement) Parser Module
Extracts structured data from MSA documents according to a predefined schema.
"""

import json
import re
import logging
from typing import Dict, Any, Optional
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


def generate_msa_extraction_prompt(schema: Dict[str, Any]) -> str:
    """Generate a detailed prompt for extracting MSA data according to the schema."""
    
    def build_schema_description(obj: Dict[str, Any], indent: int = 0) -> str:
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
    
    prompt = f"""You are an expert legal document parser specializing in Master Service Agreements (MSAs). Your task is to extract structured information from the MSA document according to the following schema.

SCHEMA STRUCTURE:
{schema_text}

INSTRUCTIONS:
1. Extract ALL information from the document that matches the schema fields
2. For mandatory fields, you MUST extract the value. If a mandatory field is not found, use null or an appropriate default
3. For optional fields, only include them if the information is present in the document
4. For enum fields, use EXACTLY one of the allowed values listed, or null if not found
5. For boolean fields, use true/false/null
6. For numeric fields, extract the numeric value (integer or float)
7. For date fields, extract dates in ISO format (YYYY-MM-DD) or as found in the document
8. For string fields, extract the exact text from the document
9. For list fields (is_list: true), create an array of objects
10. Maintain the exact nested structure as defined in the schema
11. Do NOT add fields that are not in the schema
12. Do NOT modify field names
13. If a section is not present in the document, omit it entirely (unless it's mandatory)

OUTPUT FORMAT:
Return ONLY valid JSON that matches the schema structure. The JSON should be properly formatted and parseable.

IMPORTANT:
- Extract information accurately from the document text
- Do not infer or assume values not explicitly stated
- For nested objects, maintain the exact structure
- For lists, create arrays even if there's only one item
- Use null for missing optional fields
- Use empty strings "" for missing optional string fields if that's more appropriate than null

Now, parse the following MSA document and extract the structured data:"""
    
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
        self.extraction_prompt_template = generate_msa_extraction_prompt(self.schema)
    
    def parse(self, document_text: str) -> Dict[str, Any]:
        """
        Parse MSA document text and extract structured data.
        
        Args:
            document_text: Full text content of the MSA document
            
        Returns:
            Dictionary containing structured MSA data matching the schema
        """
        # Combine prompt with document text
        full_prompt = f"{self.extraction_prompt_template}\n\n{document_text}"
        
        try:
            logger.info("Invoking LLM for MSA extraction...")
            response = self.llm.invoke(full_prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Extract JSON from response
            parsed_data = self._extract_json(response_text)
            
            # Validate structure
            self._validate_structure(parsed_data)
            
            logger.info("MSA extraction completed successfully")
            return parsed_data
            
        except Exception as e:
            logger.error(f"Error parsing MSA: {str(e)}")
            raise
    
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
        """Basic validation of extracted data structure."""
        # Check for top-level required fields
        required_top_fields = ["msa_id", "effective_date", "executed_date", "nature_of_services", "governing_law"]
        for field in required_top_fields:
            if field not in data:
                logger.warning(f"Missing required top-level field: {field}")
        
        # Check for required child objects
        if "customer" not in data:
            logger.warning("Missing required child object: customer")
        elif "authorized_signatory" not in data.get("customer", {}):
            logger.warning("Missing required customer.authorized_signatory")
        
        if "provider" not in data:
            logger.warning("Missing required child object: provider")
        elif "authorized_signatory" not in data.get("provider", {}):
            logger.warning("Missing required provider.authorized_signatory")
        
        if "services_scope" not in data:
            logger.warning("Missing required child object: services_scope")
        
        if "execution_details" not in data:
            logger.warning("Missing required child object: execution_details")
        
        logger.info("Structure validation completed")

