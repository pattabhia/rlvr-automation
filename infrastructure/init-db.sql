-- ============================================================================
-- Ground Truth Database Schema
-- ============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- DOMAINS TABLE
-- ============================================================================

CREATE TABLE domains (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    value_type VARCHAR(50) NOT NULL, -- PRICE_RANGE, JSON, CATEGORICAL, etc.
    schema JSONB NOT NULL,            -- JSON Schema for validation
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100),
    extra_metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_domains_name ON domains(name);

-- ============================================================================
-- GROUND TRUTH ENTRIES TABLE
-- ============================================================================

CREATE TABLE ground_truth_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    domain VARCHAR(100) NOT NULL,
    key VARCHAR(255) NOT NULL,
    value JSONB NOT NULL,
    value_type VARCHAR(50) NOT NULL,
    version VARCHAR(50) NOT NULL,
    valid_from TIMESTAMP NOT NULL,
    valid_to TIMESTAMP,               -- NULL = current version
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100),
    extra_metadata JSONB DEFAULT '{}'::jsonb,

    CONSTRAINT fk_domain FOREIGN KEY (domain) REFERENCES domains(name) ON DELETE CASCADE,
    CONSTRAINT unique_domain_key_version UNIQUE(domain, key, version)
);

CREATE INDEX idx_gt_domain ON ground_truth_entries(domain);
CREATE INDEX idx_gt_key ON ground_truth_entries(key);
CREATE INDEX idx_gt_domain_key ON ground_truth_entries(domain, key);
CREATE INDEX idx_gt_valid_from ON ground_truth_entries(valid_from);
CREATE INDEX idx_gt_valid_to ON ground_truth_entries(valid_to);
CREATE INDEX idx_gt_current ON ground_truth_entries(domain, key) WHERE valid_to IS NULL;

-- ============================================================================
-- GROUND TRUTH ALIASES TABLE
-- ============================================================================

CREATE TABLE ground_truth_aliases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entry_id UUID NOT NULL,
    domain VARCHAR(100) NOT NULL,
    alias VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_entry FOREIGN KEY (entry_id) REFERENCES ground_truth_entries(id) ON DELETE CASCADE,
    CONSTRAINT unique_alias UNIQUE(domain, alias)
);

CREATE INDEX idx_aliases_domain ON ground_truth_aliases(domain);
CREATE INDEX idx_aliases_alias ON ground_truth_aliases(alias);

-- ============================================================================
-- AUDIT LOG TABLE
-- ============================================================================

CREATE TABLE ground_truth_audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entry_id UUID,
    action VARCHAR(50) NOT NULL,      -- created, updated, deleted
    old_value JSONB,
    new_value JSONB,
    changed_by VARCHAR(100),
    changed_at TIMESTAMP DEFAULT NOW(),
    extra_metadata JSONB DEFAULT '{}'::jsonb,

    CONSTRAINT fk_audit_entry FOREIGN KEY (entry_id) REFERENCES ground_truth_entries(id) ON DELETE SET NULL
);

CREATE INDEX idx_audit_entry_id ON ground_truth_audit_log(entry_id);
CREATE INDEX idx_audit_changed_at ON ground_truth_audit_log(changed_at);

-- ============================================================================
-- SEED DATA: Taj Hotels Pricing Domain
-- ============================================================================

-- Create domain with detection metadata
INSERT INTO domains (name, description, value_type, schema, created_by, extra_metadata) VALUES (
    'taj_hotels_pricing',
    'Taj Hotels room pricing information',
    'PRICE_RANGE',
    '{
        "type": "object",
        "properties": {
            "min_price": {"type": "number", "minimum": 0},
            "max_price": {"type": "number", "minimum": 0},
            "currency": {"type": "string", "enum": ["INR", "USD", "EUR"]},
            "unit": {"type": "string", "enum": ["per_night", "per_person", "per_hour"]}
        },
        "required": ["min_price", "max_price", "currency", "unit"]
    }'::jsonb,
    'system',
    '{
        "detection_keywords": ["price", "cost", "rate", "charge", "expensive", "cheap", "how much", "pricing", "rates", "charges", "fee", "fees"],
        "entity_patterns": [
            "taj\\\\s+mahal\\\\s+palace",
            "taj\\\\s+lands?\\\\s+end",
            "taj\\\\s+exotica",
            "taj\\\\s+falaknuma",
            "taj\\\\s+lake\\\\s+palace",
            "taj\\\\s+rambagh",
            "taj\\\\s+bengal",
            "taj\\\\s+coromandel",
            "taj\\\\s+hotel"
        ]
    }'::jsonb
);

-- Insert Taj Hotels pricing data
INSERT INTO ground_truth_entries (domain, key, value, value_type, version, valid_from, created_by) VALUES
    ('taj_hotels_pricing', 'taj mahal palace', '{"min_price": 24000, "max_price": 65000, "currency": "INR", "unit": "per_night"}'::jsonb, 'PRICE_RANGE', '2024-12-01', '2024-01-01', 'system'),
    ('taj_hotels_pricing', 'taj lands end', '{"min_price": 18000, "max_price": 45000, "currency": "INR", "unit": "per_night"}'::jsonb, 'PRICE_RANGE', '2024-12-01', '2024-01-01', 'system'),
    ('taj_hotels_pricing', 'taj exotica goa', '{"min_price": 15000, "max_price": 40000, "currency": "INR", "unit": "per_night"}'::jsonb, 'PRICE_RANGE', '2024-12-01', '2024-01-01', 'system'),
    ('taj_hotels_pricing', 'taj falaknuma palace', '{"min_price": 35000, "max_price": 85000, "currency": "INR", "unit": "per_night"}'::jsonb, 'PRICE_RANGE', '2024-12-01', '2024-01-01', 'system'),
    ('taj_hotels_pricing', 'taj lake palace', '{"min_price": 40000, "max_price": 95000, "currency": "INR", "unit": "per_night"}'::jsonb, 'PRICE_RANGE', '2024-12-01', '2024-01-01', 'system'),
    ('taj_hotels_pricing', 'taj rambagh palace', '{"min_price": 30000, "max_price": 75000, "currency": "INR", "unit": "per_night"}'::jsonb, 'PRICE_RANGE', '2024-12-01', '2024-01-01', 'system');

-- Insert aliases
INSERT INTO ground_truth_aliases (entry_id, domain, alias)
SELECT id, 'taj_hotels_pricing', 'taj mahal palace mumbai' FROM ground_truth_entries WHERE domain = 'taj_hotels_pricing' AND key = 'taj mahal palace'
UNION ALL
SELECT id, 'taj_hotels_pricing', 'taj mahal palace colaba' FROM ground_truth_entries WHERE domain = 'taj_hotels_pricing' AND key = 'taj mahal palace'
UNION ALL
SELECT id, 'taj_hotels_pricing', 'taj mahal hotel' FROM ground_truth_entries WHERE domain = 'taj_hotels_pricing' AND key = 'taj mahal palace'
UNION ALL
SELECT id, 'taj_hotels_pricing', 'taj lands end mumbai' FROM ground_truth_entries WHERE domain = 'taj_hotels_pricing' AND key = 'taj lands end'
UNION ALL
SELECT id, 'taj_hotels_pricing', 'taj lands end bandra' FROM ground_truth_entries WHERE domain = 'taj_hotels_pricing' AND key = 'taj lands end'
UNION ALL
SELECT id, 'taj_hotels_pricing', 'taj exotica' FROM ground_truth_entries WHERE domain = 'taj_hotels_pricing' AND key = 'taj exotica goa'
UNION ALL
SELECT id, 'taj_hotels_pricing', 'taj goa' FROM ground_truth_entries WHERE domain = 'taj_hotels_pricing' AND key = 'taj exotica goa'
UNION ALL
SELECT id, 'taj_hotels_pricing', 'falaknuma palace' FROM ground_truth_entries WHERE domain = 'taj_hotels_pricing' AND key = 'taj falaknuma palace'
UNION ALL
SELECT id, 'taj_hotels_pricing', 'taj falaknuma' FROM ground_truth_entries WHERE domain = 'taj_hotels_pricing' AND key = 'taj falaknuma palace'
UNION ALL
SELECT id, 'taj_hotels_pricing', 'lake palace udaipur' FROM ground_truth_entries WHERE domain = 'taj_hotels_pricing' AND key = 'taj lake palace'
UNION ALL
SELECT id, 'taj_hotels_pricing', 'taj lake palace udaipur' FROM ground_truth_entries WHERE domain = 'taj_hotels_pricing' AND key = 'taj lake palace'
UNION ALL
SELECT id, 'taj_hotels_pricing', 'rambagh palace jaipur' FROM ground_truth_entries WHERE domain = 'taj_hotels_pricing' AND key = 'taj rambagh palace'
UNION ALL
SELECT id, 'taj_hotels_pricing', 'taj rambagh' FROM ground_truth_entries WHERE domain = 'taj_hotels_pricing' AND key = 'taj rambagh palace';

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to get current ground truth
CREATE OR REPLACE FUNCTION get_current_ground_truth(p_domain VARCHAR, p_key VARCHAR)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
BEGIN
    SELECT value INTO result
    FROM ground_truth_entries
    WHERE domain = p_domain
      AND key = p_key
      AND valid_to IS NULL
    LIMIT 1;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;

