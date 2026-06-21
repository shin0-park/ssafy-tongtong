-- 도서관 나들이 ERDCloud import용 DDL

CREATE TABLE users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(150) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    nickname VARCHAR(100),
    default_sido VARCHAR(50),
    default_sigungu VARCHAR(50),
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE TABLE libraries (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    sido VARCHAR(50) NOT NULL,
    sigungu VARCHAR(50) NOT NULL,
    library_type VARCHAR(50) NOT NULL,
    address VARCHAR(500) NOT NULL,
    latitude DECIMAL(10, 7),
    longitude DECIMAL(10, 7),
    phone VARCHAR(50),
    homepage_url VARCHAR(1000),
    closed_days VARCHAR(255),
    weekday_open_time TIME,
    weekday_close_time TIME,
    saturday_open_time TIME,
    saturday_close_time TIME,
    holiday_open_time TIME,
    holiday_close_time TIME,
    reading_seat_count INT,
    book_count INT,
    non_book_count INT,
    serial_count INT,
    loan_available_count INT,
    loan_available_days INT,
    site_area DECIMAL(12, 2),
    building_area DECIMAL(12, 2),
    operating_agency VARCHAR(255),
    data_reference_date DATE,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE TABLE library_external_codes (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    library_id BIGINT NOT NULL,
    source_name VARCHAR(100) NOT NULL,
    external_code VARCHAR(100) NOT NULL,
    external_name VARCHAR(255),
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    CONSTRAINT fk_library_external_codes_library
        FOREIGN KEY (library_id) REFERENCES libraries(id)
        ON DELETE CASCADE,
    CONSTRAINT uq_library_external_codes_source_code
        UNIQUE (source_name, external_code)
);

CREATE TABLE library_facilities (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    library_id BIGINT NOT NULL,
    facility_type VARCHAR(100) NOT NULL,
    facility_name VARCHAR(255),
    floor VARCHAR(100),
    description TEXT,
    source_type VARCHAR(100),
    source_url VARCHAR(1000),
    confidence DECIMAL(5, 2),
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    CONSTRAINT fk_library_facilities_library
        FOREIGN KEY (library_id) REFERENCES libraries(id)
        ON DELETE CASCADE
);

CREATE TABLE tags (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(100) NOT NULL UNIQUE,
    label VARCHAR(100) NOT NULL,
    tag_group VARCHAR(100) NOT NULL,
    description TEXT,
    is_dynamic BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE TABLE library_tags (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    library_id BIGINT NOT NULL,
    tag_id BIGINT NOT NULL,
    source_type VARCHAR(100),
    source_url VARCHAR(1000),
    confidence DECIMAL(5, 2),
    score DECIMAL(8, 2),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    expires_at DATETIME,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    CONSTRAINT fk_library_tags_library
        FOREIGN KEY (library_id) REFERENCES libraries(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_library_tags_tag
        FOREIGN KEY (tag_id) REFERENCES tags(id)
        ON DELETE CASCADE,
    CONSTRAINT uq_library_tags_library_tag_source
        UNIQUE (library_id, tag_id, source_type)
);

CREATE TABLE purposes (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(100) NOT NULL UNIQUE,
    label VARCHAR(100) NOT NULL,
    description TEXT,
    display_order INT NOT NULL DEFAULT 0
);

CREATE TABLE purpose_tag_rules (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    purpose_id BIGINT NOT NULL,
    tag_id BIGINT NOT NULL,
    weight DECIMAL(8, 2) NOT NULL DEFAULT 1.00,
    is_required BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    CONSTRAINT fk_purpose_tag_rules_purpose
        FOREIGN KEY (purpose_id) REFERENCES purposes(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_purpose_tag_rules_tag
        FOREIGN KEY (tag_id) REFERENCES tags(id)
        ON DELETE CASCADE,
    CONSTRAINT uq_purpose_tag_rules_purpose_tag
        UNIQUE (purpose_id, tag_id)
);

CREATE TABLE programs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    library_id BIGINT NOT NULL,
    external_program_id VARCHAR(100),
    title VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    target VARCHAR(255),
    start_date DATE,
    end_date DATE,
    apply_start_date DATE,
    apply_end_date DATE,
    place VARCHAR(255),
    capacity INT,
    fee VARCHAR(100),
    status VARCHAR(100),
    description TEXT,
    source_url VARCHAR(1000),
    apply_url VARCHAR(1000),
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    CONSTRAINT fk_programs_library
        FOREIGN KEY (library_id) REFERENCES libraries(id)
        ON DELETE CASCADE
);

CREATE TABLE reading_room_status_snapshots (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    library_id BIGINT NOT NULL,
    external_library_id VARCHAR(100),
    external_room_id VARCHAR(100),
    room_no VARCHAR(50),
    room_name VARCHAR(255),
    room_type VARCHAR(100),
    floor_info VARCHAR(100),
    current_visitor_count INT,
    total_seats INT,
    used_seats INT,
    reserved_seats INT,
    available_seats INT,
    occupancy_rate DECIMAL(6, 2),
    status VARCHAR(50) NOT NULL DEFAULT 'unknown',
    source_updated_at DATETIME,
    fetched_at DATETIME NOT NULL,
    CONSTRAINT fk_reading_room_status_snapshots_library
        FOREIGN KEY (library_id) REFERENCES libraries(id)
        ON DELETE CASCADE
);

CREATE TABLE books (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    isbn13 VARCHAR(13) NOT NULL UNIQUE,
    isbn VARCHAR(20),
    set_isbn13 VARCHAR(13),
    title VARCHAR(500) NOT NULL,
    author VARCHAR(500),
    publisher VARCHAR(255),
    publication_year VARCHAR(20),
    publication_date DATE,
    volume VARCHAR(100),
    kdc_class_no VARCHAR(50),
    kdc_class_name VARCHAR(255),
    isbn_addition_symbol VARCHAR(20),
    description TEXT,
    cover_url VARCHAR(1000),
    book_detail_url VARCHAR(1000),
    source_type VARCHAR(100),
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE TABLE library_books (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    library_id BIGINT NOT NULL,
    book_id BIGINT NOT NULL,
    external_library_code VARCHAR(100),
    call_number VARCHAR(255),
    separate_shelf_code VARCHAR(100),
    separate_shelf_name VARCHAR(255),
    book_code VARCHAR(100),
    shelf_location_code VARCHAR(100),
    shelf_location_name VARCHAR(255),
    copy_code VARCHAR(100),
    registered_date DATE,
    has_book BOOLEAN,
    is_loan_available BOOLEAN,
    availability_checked_at DATETIME,
    source_type VARCHAR(100),
    updated_at DATETIME NOT NULL,
    CONSTRAINT fk_library_books_library
        FOREIGN KEY (library_id) REFERENCES libraries(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_library_books_book
        FOREIGN KEY (book_id) REFERENCES books(id)
        ON DELETE CASCADE,
    CONSTRAINT uq_library_books_library_book
        UNIQUE (library_id, book_id)
);

CREATE TABLE book_ranking_snapshots (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    book_id BIGINT NOT NULL,
    library_id BIGINT,
    region_sido VARCHAR(50),
    region_sigungu VARCHAR(50),
    region_code VARCHAR(20),
    detail_region_code VARCHAR(20),
    ranking_type VARCHAR(100) NOT NULL,
    source_isbn13 VARCHAR(13),
    ranking INT,
    loan_count INT,
    score DECIMAL(10, 2),
    period_start DATE,
    period_end DATE,
    age_group VARCHAR(50),
    gender VARCHAR(50),
    kdc_class_no VARCHAR(50),
    target_group VARCHAR(100),
    created_at DATETIME NOT NULL,
    fetched_at DATETIME NOT NULL,
    CONSTRAINT fk_book_ranking_snapshots_book
        FOREIGN KEY (book_id) REFERENCES books(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_book_ranking_snapshots_library
        FOREIGN KEY (library_id) REFERENCES libraries(id)
        ON DELETE SET NULL
);

CREATE TABLE library_images (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    library_id BIGINT NOT NULL,
    image_url VARCHAR(1000),
    local_path VARCHAR(1000),
    image_type VARCHAR(100),
    source_name VARCHAR(255),
    source_url VARCHAR(1000),
    license_type VARCHAR(100),
    attribution_text TEXT,
    is_main BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    display_order INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL,
    CONSTRAINT fk_library_images_library
        FOREIGN KEY (library_id) REFERENCES libraries(id)
        ON DELETE CASCADE
);

CREATE TABLE user_library_saves (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    library_id BIGINT NOT NULL,
    memo TEXT,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    CONSTRAINT fk_user_library_saves_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_user_library_saves_library
        FOREIGN KEY (library_id) REFERENCES libraries(id)
        ON DELETE CASCADE,
    CONSTRAINT uq_user_library_saves_user_library
        UNIQUE (user_id, library_id)
);

CREATE TABLE user_reviews (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    library_id BIGINT NOT NULL,
    rating TINYINT NOT NULL,
    content TEXT NOT NULL,
    visit_purpose VARCHAR(100),
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    CONSTRAINT fk_user_reviews_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_user_reviews_library
        FOREIGN KEY (library_id) REFERENCES libraries(id)
        ON DELETE CASCADE
);

CREATE TABLE user_review_images (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    review_id BIGINT NOT NULL,
    image VARCHAR(1000),
    image_url VARCHAR(1000),
    alt_text VARCHAR(255),
    display_order INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL,
    CONSTRAINT fk_user_review_images_review
        FOREIGN KEY (review_id) REFERENCES user_reviews(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_libraries_region ON libraries (sido, sigungu);
CREATE INDEX idx_libraries_location ON libraries (latitude, longitude);
CREATE INDEX idx_library_external_codes_library ON library_external_codes (library_id);
CREATE INDEX idx_library_facilities_library ON library_facilities (library_id);
CREATE INDEX idx_library_tags_library ON library_tags (library_id);
CREATE INDEX idx_library_tags_tag ON library_tags (tag_id);
CREATE INDEX idx_programs_library ON programs (library_id);
CREATE INDEX idx_programs_date ON programs (start_date, end_date);
CREATE INDEX idx_reading_room_snapshots_library_fetched ON reading_room_status_snapshots (library_id, fetched_at);
CREATE INDEX idx_books_title ON books (title);
CREATE INDEX idx_library_books_book ON library_books (book_id);
CREATE INDEX idx_book_ranking_type_fetched ON book_ranking_snapshots (ranking_type, fetched_at);
CREATE INDEX idx_library_images_library ON library_images (library_id);
CREATE INDEX idx_user_reviews_library ON user_reviews (library_id);
