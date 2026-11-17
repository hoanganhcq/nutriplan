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
    source_url TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS MEAL (
    meal_id INTEGER PRIMARY KEY AUTO_INCREMENT,
    household_id INTEGER NOT NULL,
    created_by_member_id INTEGER,
    eaten_at DATETIME NOT NULL,
    image_path TEXT,
    status VARCHAR(30) DEFAULT 'pending',
    INDEX idx_meal_household_eaten_at (household_id, eaten_at),
    FOREIGN KEY (household_id) REFERENCES HOUSEHOLD(household_id),
    FOREIGN KEY (created_by_member_id) REFERENCES MEMBER(member_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS MEAL_ITEM (
    meal_item_id INTEGER PRIMARY KEY AUTO_INCREMENT,
    meal_id INTEGER NOT NULL,
    food_id INTEGER NOT NULL,
    estimated_weight_g DECIMAL(8,2),
    confirmed_weight_g DECIMAL(8,2),
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
    INDEX idx_menu_plan_member_start_date (member_id, start_date),
    FOREIGN KEY (member_id) REFERENCES MEMBER(member_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS MENU_ITEM (
    menu_item_id INTEGER PRIMARY KEY AUTO_INCREMENT,
    menu_plan_id INTEGER NOT NULL,
    food_id INTEGER NOT NULL,
    meal_type VARCHAR(30) NOT NULL,
    portion_g DECIMAL(8,2),
    INDEX idx_menu_item_menu_plan (menu_plan_id),
    FOREIGN KEY (menu_plan_id) REFERENCES MENU_PLAN(menu_plan_id),
    FOREIGN KEY (food_id) REFERENCES FOOD_ITEM(food_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
