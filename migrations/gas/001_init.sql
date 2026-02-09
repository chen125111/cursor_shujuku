CREATE TABLE IF NOT EXISTS gas_mixture (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    temperature DOUBLE NOT NULL,
    x_ch4 DOUBLE DEFAULT 0,
    x_c2h6 DOUBLE DEFAULT 0,
    x_c3h8 DOUBLE DEFAULT 0,
    x_co2 DOUBLE DEFAULT 0,
    x_n2 DOUBLE DEFAULT 0,
    x_h2s DOUBLE DEFAULT 0,
    x_ic4h10 DOUBLE DEFAULT 0,
    pressure DOUBLE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS pending_review (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    group_id VARCHAR(32) NOT NULL,
    original_id BIGINT,
    temperature DOUBLE NOT NULL,
    x_ch4 DOUBLE DEFAULT 0,
    x_c2h6 DOUBLE DEFAULT 0,
    x_c3h8 DOUBLE DEFAULT 0,
    x_co2 DOUBLE DEFAULT 0,
    x_n2 DOUBLE DEFAULT 0,
    x_h2s DOUBLE DEFAULT 0,
    x_ic4h10 DOUBLE DEFAULT 0,
    pressure DOUBLE NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP NULL,
    reviewed_by VARCHAR(64)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX idx_gas_temperature ON gas_mixture(temperature);
CREATE INDEX idx_gas_pressure ON gas_mixture(pressure);
CREATE INDEX idx_gas_temp_pressure ON gas_mixture(temperature, pressure);
CREATE INDEX idx_gas_x_ch4 ON gas_mixture(x_ch4);
CREATE INDEX idx_gas_x_c2h6 ON gas_mixture(x_c2h6);
CREATE INDEX idx_gas_x_c3h8 ON gas_mixture(x_c3h8);
CREATE INDEX idx_gas_x_co2 ON gas_mixture(x_co2);
CREATE INDEX idx_gas_x_n2 ON gas_mixture(x_n2);
CREATE INDEX idx_gas_x_h2s ON gas_mixture(x_h2s);
CREATE INDEX idx_gas_x_ic4h10 ON gas_mixture(x_ic4h10);
CREATE INDEX idx_pending_group ON pending_review(group_id);
CREATE INDEX idx_pending_status ON pending_review(status);
CREATE INDEX idx_pending_group_status ON pending_review(group_id, status);
