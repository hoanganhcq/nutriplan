CREATE TABLE IF NOT EXISTS SESSION (
    session_id INTEGER PRIMARY KEY AUTO_INCREMENT,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS HOUSEHOLD (
    household_id INTEGER PRIMARY KEY AUTO_INCREMENT,
    session_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    INDEX idx_household_session (session_id),
    FOREIGN KEY (session_id) REFERENCES SESSION(session_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS MEMBER (
    member_id INTEGER PRIMARY KEY AUTO_INCREMENT,
    household_id INTEGER NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    age INTEGER,
    sex VARCHAR(20),
    weight_kg DECIMAL(5,2),
    height_cm DECIMAL(5,2),
    health_conditions TEXT,
    allergies TEXT,
    preferences TEXT,
    energy_target_kcal INTEGER,
    texture_requirements VARCHAR(20),
    is_simulated BOOLEAN NOT NULL DEFAULT FALSE,
    profile_version INTEGER NOT NULL DEFAULT 1,
    INDEX idx_member_household (household_id),
    FOREIGN KEY (household_id) REFERENCES HOUSEHOLD(household_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS FOOD_ITEM (
    food_id INTEGER PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(150) NOT NULL,
    category VARCHAR(50),
    kcal_per_100g DECIMAL(8,2),
    protein_per_100g DECIMAL(8,2),
    carb_per_100g DECIMAL(8,2),
    fat_per_100g DECIMAL(8,2),
    source_name VARCHAR(150),
    source_url TEXT,
    entity_type VARCHAR(20) NOT NULL DEFAULT 'DISH',
    aliases TEXT,
    default_portion_g DECIMAL(8,2),
    sugar_per_100g DECIMAL(8,2),
    fiber_per_100g DECIMAL(8,2),
    sodium_mg_per_100g DECIMAL(8,2),
    potassium_mg_per_100g DECIMAL(8,2),
    phosphorus_mg_per_100g DECIMAL(8,2),
    ingredients TEXT,
    allergen_codes TEXT,
    allergen_verified BOOLEAN NOT NULL DEFAULT FALSE,
    texture VARCHAR(20),
    cooking_effort VARCHAR(20),
    INDEX idx_food_item_category_food (category, food_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS MEAL (
    meal_id INTEGER PRIMARY KEY AUTO_INCREMENT,
    household_id INTEGER NOT NULL,
    created_by_member_id INTEGER,
    eaten_at DATETIME NOT NULL,
    image_path TEXT,
    status VARCHAR(30) DEFAULT 'pending',
    meal_type VARCHAR(30),
    revision INTEGER NOT NULL DEFAULT 1,
    image_count INTEGER NOT NULL DEFAULT 0,
    is_estimate BOOLEAN NOT NULL DEFAULT TRUE,
    warnings TEXT,
    confirmed_at DATETIME,
    note TEXT,
    INDEX idx_meal_household_eaten_at (household_id, eaten_at),
    INDEX idx_meal_status_eaten (status, eaten_at),
    FOREIGN KEY (household_id) REFERENCES HOUSEHOLD(household_id),
    FOREIGN KEY (created_by_member_id) REFERENCES MEMBER(member_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS MEAL_REVISION_HISTORY (
    revision_id INT AUTO_INCREMENT PRIMARY KEY,
    meal_id INT NOT NULL,
    revision_no INT NOT NULL,
    action VARCHAR(30) NOT NULL,
    snapshot_json JSON NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_MEAL_REVISION_MEAL FOREIGN KEY (meal_id)
        REFERENCES MEAL(meal_id) ON DELETE CASCADE,
    CONSTRAINT unique_meal_revision UNIQUE (meal_id, revision_no)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS MEAL_ITEM (
    meal_item_id INTEGER PRIMARY KEY AUTO_INCREMENT,
    meal_id INTEGER NOT NULL,
    food_id INTEGER NOT NULL,
    estimated_weight_g DECIMAL(8,2),
    confirmed_weight_g DECIMAL(8,2),
    seasoning TEXT,
    confidence DECIMAL(4,3),
    INDEX idx_meal_item_meal (meal_id),
    FOREIGN KEY (meal_id) REFERENCES MEAL(meal_id),
    FOREIGN KEY (food_id) REFERENCES FOOD_ITEM(food_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ASSESSMENT (
    assessment_id INTEGER PRIMARY KEY AUTO_INCREMENT,
    meal_id INTEGER NOT NULL,
    member_id INTEGER NOT NULL,
    suitability_level VARCHAR(30) NOT NULL,
    explanation TEXT,
    suggestion_text TEXT,
    created_at DATETIME NOT NULL,
    meal_revision INTEGER NOT NULL DEFAULT 1,
    profile_version INTEGER NOT NULL DEFAULT 1,
    ruleset_version VARCHAR(30),
    reasons TEXT,
    UNIQUE (meal_id, member_id),
    INDEX idx_assessment_member (member_id),
    FOREIGN KEY (meal_id) REFERENCES MEAL(meal_id),
    FOREIGN KEY (member_id) REFERENCES MEMBER(member_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS MENU_PLAN (
    menu_plan_id INTEGER PRIMARY KEY AUTO_INCREMENT,
    member_id INTEGER NOT NULL,
    start_date DATE NOT NULL,
    duration_days INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(30) DEFAULT 'draft',
    revision INTEGER NOT NULL DEFAULT 1,
    validation_json TEXT,
    soft_score_json TEXT,
    generation_json TEXT,
    soft_score DECIMAL(5,2),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_menu_plan_member_start_date (member_id, start_date),
    FOREIGN KEY (member_id) REFERENCES MEMBER(member_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS MENU_ITEM (
    menu_item_id INTEGER PRIMARY KEY AUTO_INCREMENT,
    menu_plan_id INTEGER NOT NULL,
    food_id INTEGER NOT NULL,
    meal_type VARCHAR(30) NOT NULL,
    portion_g DECIMAL(8,2),
    day_index TINYINT NOT NULL DEFAULT 1,
    locked BOOLEAN NOT NULL DEFAULT FALSE,
    INDEX idx_menu_item_menu_plan (menu_plan_id),
    FOREIGN KEY (menu_plan_id) REFERENCES MENU_PLAN(menu_plan_id),
    FOREIGN KEY (food_id) REFERENCES FOOD_ITEM(food_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS MENU_PLAN_REVISION_HISTORY (
    menu_plan_id INTEGER NOT NULL,
    revision INTEGER NOT NULL,
    snapshot_json MEDIUMTEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (menu_plan_id, revision),
    FOREIGN KEY (menu_plan_id) REFERENCES MENU_PLAN(menu_plan_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS CONSENT (
    household_id INTEGER NOT NULL,
    consent_type VARCHAR(50) NOT NULL,
    granted BOOLEAN NOT NULL,
    policy_version VARCHAR(30) NOT NULL,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (household_id, consent_type),
    FOREIGN KEY (household_id) REFERENCES HOUSEHOLD(household_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS CONSENT_HISTORY (
    consent_history_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    household_id INTEGER NOT NULL,
    consent_type VARCHAR(50) NOT NULL,
    granted BOOLEAN NOT NULL,
    policy_version VARCHAR(30) NOT NULL,
    changed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_consent_history_household (household_id, changed_at),
    FOREIGN KEY (household_id) REFERENCES HOUSEHOLD(household_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS MEAL_MEMBER (
    meal_id INTEGER NOT NULL,
    member_id INTEGER NOT NULL,
    PRIMARY KEY (meal_id, member_id),
    INDEX idx_meal_member_member (member_id),
    FOREIGN KEY (meal_id) REFERENCES MEAL(meal_id),
    FOREIGN KEY (member_id) REFERENCES MEMBER(member_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS NUTRITION_RULE (
    rule_id INTEGER PRIMARY KEY AUTO_INCREMENT,
    rule_type VARCHAR(50) NOT NULL,
    subject VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    ruleset_version VARCHAR(30) NOT NULL,
    source_name VARCHAR(150) NOT NULL,
    source_url TEXT NOT NULL,
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    INDEX idx_rule_active_verified (active, verified, rule_type, subject),
    UNIQUE KEY uq_rule_version (rule_type, subject, ruleset_version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS RULE_SOURCE (
    source_id INT AUTO_INCREMENT PRIMARY KEY,
    organization VARCHAR(200) NOT NULL,
    title VARCHAR(300) NOT NULL,
    published_year SMALLINT,
    applicability VARCHAR(300),
    source_url TEXT,
    updated_at DATE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS HEALTH_RULE (
    rule_id INT AUTO_INCREMENT PRIMARY KEY,
    rule_code VARCHAR(80) NOT NULL UNIQUE,
    condition_code VARCHAR(20) NOT NULL,
    nutrient VARCHAR(30) NOT NULL,
    scope VARCHAR(10) NOT NULL,
    operator VARCHAR(5) NOT NULL,
    threshold DECIMAL(10,2) NOT NULL,
    unit VARCHAR(10) NOT NULL,
    severity VARCHAR(10) NOT NULL,
    source_id INT,
    version VARCHAR(20) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    rationale TEXT,
    change_log TEXT,
    INDEX idx_health_rule_enabled_filter
        (enabled, condition_code, nutrient, scope),
    CONSTRAINT fk_HEALTH_RULE_SOURCE FOREIGN KEY (source_id)
        REFERENCES RULE_SOURCE(source_id) ON DELETE RESTRICT,
    CONSTRAINT chk_rule_severity CHECK (severity IN ('YELLOW', 'RED')),
    CONSTRAINT chk_rule_enabled_has_source
        CHECK (enabled = FALSE OR source_id IS NOT NULL)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
