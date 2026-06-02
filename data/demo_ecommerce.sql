DROP TABLE IF EXISTS support_tickets;
DROP TABLE IF EXISTS shipments;
DROP TABLE IF EXISTS refunds;
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    city TEXT NOT NULL,
    segment TEXT NOT NULL,
    signup_date TEXT NOT NULL
);

CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    sku TEXT NOT NULL UNIQUE,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    unit_price_cents INTEGER NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    order_date TEXT NOT NULL,
    status TEXT NOT NULL,
    channel TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE order_items (
    order_item_id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price_cents INTEGER NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE payments (
    payment_id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL,
    paid_at TEXT NOT NULL,
    amount_cents INTEGER NOT NULL,
    method TEXT NOT NULL,
    status TEXT NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);

CREATE TABLE refunds (
    refund_id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL,
    refunded_at TEXT NOT NULL,
    amount_cents INTEGER NOT NULL,
    reason TEXT NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);

CREATE TABLE shipments (
    shipment_id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL,
    shipped_at TEXT,
    delivered_at TEXT,
    carrier TEXT NOT NULL,
    status TEXT NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);

CREATE TABLE support_tickets (
    ticket_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    order_id INTEGER,
    created_at TEXT NOT NULL,
    issue_type TEXT NOT NULL,
    priority TEXT NOT NULL,
    status TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);

INSERT INTO customers VALUES
    (1, 'Maya Chen', 'maya.chen@example.com', 'Seattle', 'Enterprise', '2023-01-18'),
    (2, 'Omar Ali', 'omar.ali@example.com', 'Austin', 'Startup', '2023-03-04'),
    (3, 'Priya Nair', 'priya.nair@example.com', 'New York', 'Enterprise', '2023-05-21'),
    (4, 'Lucas Rivera', 'lucas.rivera@example.com', 'Chicago', 'SMB', '2023-07-09'),
    (5, 'Nina Patel', 'nina.patel@example.com', 'Seattle', 'Startup', '2023-09-17'),
    (6, 'Ethan Brooks', 'ethan.brooks@example.com', 'Denver', 'SMB', '2023-11-02');

INSERT INTO products VALUES
    (1, 'ANL-100', 'Analytics Starter Kit', 'Analytics', 12900, 1),
    (2, 'ANL-200', 'Analytics Pro Kit', 'Analytics', 24900, 1),
    (3, 'SEC-100', 'Security Audit Pack', 'Security', 19900, 1),
    (4, 'OPS-100', 'Ops Automation Pack', 'Operations', 17900, 1),
    (5, 'DSN-100', 'Dashboard Templates', 'Analytics', 5900, 1),
    (6, 'SUP-100', 'Priority Support Add-on', 'Support', 9900, 1);

INSERT INTO orders VALUES
    (101, 1, '2024-01-12', 'completed', 'sales'),
    (102, 2, '2024-01-21', 'completed', 'self-serve'),
    (103, 3, '2024-02-03', 'completed', 'sales'),
    (104, 1, '2024-02-14', 'completed', 'sales'),
    (105, 4, '2024-02-27', 'cancelled', 'self-serve'),
    (106, 5, '2024-03-06', 'completed', 'partner'),
    (107, 6, '2024-03-19', 'processing', 'self-serve'),
    (108, 3, '2024-03-22', 'completed', 'sales'),
    (109, 2, '2024-04-02', 'completed', 'partner'),
    (110, 5, '2024-04-13', 'completed', 'self-serve'),
    (111, 4, '2024-04-28', 'processing', 'sales'),
    (112, 1, '2024-05-08', 'completed', 'sales');

INSERT INTO order_items VALUES
    (1001, 101, 2, 2, 24900),
    (1002, 101, 6, 1, 9900),
    (1003, 102, 1, 1, 12900),
    (1004, 102, 5, 2, 5900),
    (1005, 103, 3, 2, 19900),
    (1006, 103, 6, 1, 9900),
    (1007, 104, 4, 3, 17900),
    (1008, 105, 1, 1, 12900),
    (1009, 106, 2, 1, 24900),
    (1010, 106, 5, 4, 5900),
    (1011, 107, 6, 1, 9900),
    (1012, 108, 3, 1, 19900),
    (1013, 108, 4, 2, 17900),
    (1014, 109, 1, 2, 12900),
    (1015, 110, 2, 1, 24900),
    (1016, 110, 6, 1, 9900),
    (1017, 111, 4, 1, 17900),
    (1018, 112, 3, 1, 19900),
    (1019, 112, 2, 1, 24900);

INSERT INTO payments VALUES
    (5001, 101, '2024-01-12', 59700, 'card', 'paid'),
    (5002, 102, '2024-01-21', 24700, 'card', 'paid'),
    (5003, 103, '2024-02-03', 49700, 'wire', 'paid'),
    (5004, 104, '2024-02-14', 53700, 'wire', 'paid'),
    (5005, 105, '2024-02-27', 0, 'card', 'voided'),
    (5006, 106, '2024-03-06', 48500, 'card', 'paid'),
    (5007, 107, '2024-03-19', 9900, 'card', 'authorized'),
    (5008, 108, '2024-03-22', 55700, 'wire', 'paid'),
    (5009, 109, '2024-04-02', 25800, 'card', 'paid'),
    (5010, 110, '2024-04-13', 34800, 'card', 'paid'),
    (5011, 111, '2024-04-28', 17900, 'wire', 'authorized'),
    (5012, 112, '2024-05-08', 44800, 'wire', 'paid');

INSERT INTO refunds VALUES
    (7001, 103, '2024-02-11', 9900, 'support add-on removed'),
    (7002, 110, '2024-04-20', 9900, 'duplicate add-on');

INSERT INTO shipments VALUES
    (8001, 101, '2024-01-13', '2024-01-16', 'UPS', 'delivered'),
    (8002, 102, '2024-01-22', '2024-01-25', 'FedEx', 'delivered'),
    (8003, 103, '2024-02-04', '2024-02-07', 'UPS', 'delivered'),
    (8004, 104, '2024-02-15', '2024-02-18', 'DHL', 'delivered'),
    (8005, 106, '2024-03-07', '2024-03-11', 'FedEx', 'delivered'),
    (8006, 107, '2024-03-20', NULL, 'UPS', 'in_transit'),
    (8007, 108, '2024-03-23', '2024-03-27', 'DHL', 'delivered'),
    (8008, 109, '2024-04-03', '2024-04-06', 'FedEx', 'delivered'),
    (8009, 110, '2024-04-14', '2024-04-16', 'UPS', 'delivered'),
    (8010, 111, NULL, NULL, 'DHL', 'pending'),
    (8011, 112, '2024-05-09', NULL, 'UPS', 'in_transit');

INSERT INTO support_tickets VALUES
    (9001, 1, 101, '2024-01-14', 'invoice', 'low', 'closed'),
    (9002, 3, 103, '2024-02-06', 'refund', 'medium', 'closed'),
    (9003, 6, 107, '2024-03-21', 'shipping', 'high', 'open'),
    (9004, 5, 110, '2024-04-16', 'refund', 'medium', 'open'),
    (9005, 4, 111, '2024-04-29', 'shipping', 'high', 'open');

