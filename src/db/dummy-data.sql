-- Seed dummy data for the project schema.
-- Safe cleanup in FK order
DELETE FROM orderlines;
DELETE FROM orders;
DELETE FROM cart;
DELETE FROM search;
DELETE FROM viewedProduct;
DELETE FROM sessions;
DELETE FROM products;
DELETE FROM customers;
DELETE FROM users;

-- Users (include both customers and a sales user)
INSERT INTO users(uid, pwd, role) VALUES
  (1001, 'pass1001', 'customer'),
  (1002, 'pass1002', 'customer'),
  (9001, 'sales9001', 'sales');

-- Customers (cid references users.uid)
INSERT INTO customers(cid, name, email) VALUES
  (1001, 'Alice Johnson', 'alice@example.com'),
  (1002, 'Bob Smith', 'bob@example.com');

-- Products
INSERT INTO products(pid, name, category, price, stock_count, descr) VALUES
  (2001, 'Wireless Mouse', 'Electronics', 24.99, 120, 'Ergonomic 2.4GHz optical mouse'),
  (2002, 'Mechanical Keyboard', 'Electronics', 79.50, 75, 'RGB backlit, blue switches'),
  (2003, 'USB-C Cable 1m', 'Accessories', 9.95, 500, 'Durable braided USB-C to USB-C cable'),
  (2004, 'Notebook A5', 'Stationery', 5.25, 300, 'Ruled, 100 pages'),
  (2005, 'Insulated Bottle 750ml', 'Outdoors', 29.00, 60, 'Keeps drinks cold for 24h'),
  (2006, 'Bluetooth Speaker', 'Electronics', 39.99, 90, 'Portable speaker with deep bass');

-- Additional 50 products to enrich catalog
INSERT INTO products(pid, name, category, price, stock_count, descr) VALUES
  (2007, '27" 4K Monitor', 'Electronics', 279.99, 45, 'IPS panel with HDR10 support'),
  (2008, 'Laptop Stand Aluminum', 'Accessories', 34.95, 150, 'Adjustable ergonomic riser'),
  (2009, 'Wireless Earbuds', 'Electronics', 59.99, 200, 'Bluetooth 5.3 with charging case'),
  (2010, 'Gaming Mouse Pad XL', 'Accessories', 14.99, 250, 'Anti-slip rubber base, stitched edges'),
  (2011, 'Webcam 1080p', 'Electronics', 39.50, 120, 'Auto light correction, dual mics'),
  (2012, 'Portable SSD 1TB', 'Electronics', 89.00, 80, 'USB 3.2 Gen2, up to 1,000MB/s'),
  (2013, 'Smart LED Bulb', 'Home', 12.99, 300, 'Color-changing, voice assistant compatible'),
  (2014, 'Surge Protector 8-Outlet', 'Home', 21.49, 140, '2100 Joules with 4 USB ports'),
  (2015, 'Office Chair Cushion', 'Home', 19.99, 110, 'Memory foam seat cushion'),
  (2016, 'Desk Organizer Tray', 'Stationery', 11.49, 180, 'Multi-compartment mesh organizer'),
  (2017, 'Gel Pens 12-Pack', 'Stationery', 8.25, 220, '0.7mm smooth writing pens'),
  (2018, 'Sticky Notes 10-Pack', 'Stationery', 6.75, 260, 'Assorted colors, 100 sheets each'),
  (2019, 'Fountain Pen', 'Stationery', 17.99, 90, 'Fine nib with refillable converter'),
  (2020, 'Graphic Drawing Tablet', 'Electronics', 69.99, 65, '8192 pressure levels, 10x6 inch'),
  (2021, 'Noise Cancelling Headphones', 'Electronics', 129.00, 55, 'Over-ear ANC with 40h battery'),
  (2022, 'Action Camera 4K', 'Electronics', 99.00, 70, 'Waterproof housing included'),
  (2023, 'Tripod Lightweight', 'Photography', 24.49, 130, 'Aluminum, 60 inch, carry bag'),
  (2024, 'Ring Light 12"', 'Photography', 27.99, 115, 'Dimmable with phone holder'),
  (2025, 'Reusable Coffee Cup 16oz', 'Outdoors', 13.50, 160, 'Leakproof lid, BPA-free'),
  (2026, 'Camping Lantern', 'Outdoors', 22.99, 95, 'Rechargeable, 1000 lumen'),
  (2027, 'Hiking Backpack 30L', 'Outdoors', 49.99, 60, 'Water-resistant, ventilated back'),
  (2028, 'Yoga Mat', 'Outdoors', 18.99, 140, 'Non-slip, 6mm thick'),
  (2029, 'Stainless Steel Straws', 'Home', 7.99, 300, '8-pack with cleaning brush'),
  (2030, 'Air Fryer 4Qt', 'Home', 79.99, 50, 'Digital controls, non-stick basket'),
  (2031, 'Electric Kettle 1.7L', 'Home', 29.99, 90, 'Auto shut-off, fast boil'),
  (2032, 'Chef Knife 8"', 'Home', 24.99, 120, 'High-carbon stainless steel'),
  (2033, 'Cutting Board Bamboo', 'Home', 15.49, 150, 'Juice groove, large size'),
  (2034, 'Water Filter Pitcher', 'Home', 27.50, 80, 'Removes chlorine and metals'),
  (2035, 'Ceramic Plant Pot 6"', 'Home', 14.25, 130, 'With drainage hole and saucer'),
  (2036, 'LED Desk Lamp', 'Home', 23.99, 110, 'Adjustable color temperature'),
  (2037, 'Phone Stand', 'Accessories', 9.49, 240, 'Aluminum, multi-angle'),
  (2038, 'MagSafe Charger', 'Electronics', 34.99, 100, '15W fast wireless charging'),
  (2039, 'Power Bank 20,000mAh', 'Electronics', 29.99, 150, 'PD 20W, dual USB-C/USB-A'),
  (2040, 'HDMI Cable 2m', 'Accessories', 8.99, 300, '8K/60Hz ultra high speed'),
  (2041, 'Ethernet Cable Cat6 5m', 'Accessories', 10.49, 220, 'Flat, snagless connectors'),
  (2042, 'NVMe SSD 2TB', 'Electronics', 139.00, 40, 'PCIe 4.0 up to 7,000MB/s'),
  (2043, 'External HDD 4TB', 'Electronics', 84.99, 70, 'USB 3.0 desktop drive'),
  (2044, 'Smart Plug', 'Home', 11.99, 210, 'Wi-Fi plug with energy monitoring'),
  (2045, 'Robot Vacuum', 'Home', 179.00, 35, 'Slim design, app control'),
  (2046, 'Mechanical Pencil 0.5mm', 'Stationery', 4.99, 260, 'Metal body with grip'),
  (2047, 'Binder Clips 24-Pack', 'Stationery', 5.49, 280, 'Assorted sizes and colors'),
  (2048, 'Index Cards 500-Pack', 'Stationery', 7.49, 200, 'Lined, 3x5 inches'),
  (2049, 'Whiteboard Markers 8-Pack', 'Stationery', 9.99, 170, 'Low odor, chisel tip'),
  (2050, 'Desk Mat PU Leather', 'Accessories', 16.99, 140, 'Dual-sided, 31x15 inches'),
  (2051, 'USB-C Hub 7-in-1', 'Electronics', 26.99, 130, 'HDMI, PD, SD/TF, USB 3.0'),
  (2052, 'Portable Projector', 'Electronics', 119.00, 40, '1080p supported, Wi-Fi'),
  (2053, 'Fitness Tracker', 'Electronics', 44.99, 150, 'Heart rate, sleep, GPS'),
  (2054, 'Smartwatch', 'Electronics', 149.00, 50, 'AMOLED display, GPS, NFC'),
  (2055, 'Desk Drawer Unit', 'Home', 59.99, 30, '3-tier rolling storage'),
  (2056, 'Cable Management Kit', 'Accessories', 12.49, 190, 'Sleeves, clips, zip ties');

-- Sessions for customers
INSERT INTO sessions(cid, sessionNo, start_time, end_time) VALUES
  (1001, 1, '2025-10-25 09:00:00', '2025-10-25 10:15:00'),
  (1001, 2, '2025-10-28 18:30:00', NULL),
  (1002, 1, '2025-10-26 14:05:00', '2025-10-26 14:45:00');

-- Viewed products timeline
INSERT INTO viewedProduct(cid, sessionNo, ts, pid) VALUES
  (1001, 1, '2025-10-25 09:05:10', 2001),
  (1001, 1, '2025-10-25 09:07:45', 2002),
  (1001, 1, '2025-10-25 09:12:03', 2003),
  (1002, 1, '2025-10-26 14:06:10', 2005),
  (1002, 1, '2025-10-26 14:10:50', 2006),
  (1001, 2, '2025-10-28 18:31:25', 2006);

-- Searches performed
INSERT INTO search(cid, sessionNo, ts, query) VALUES
  (1001, 1, '2025-10-25 09:02:00', 'mouse'),
  (1001, 1, '2025-10-25 09:08:00', 'keyboard'),
  (1002, 1, '2025-10-26 14:06:40', 'bottle'),
  (1001, 2, '2025-10-28 18:32:00', 'speaker');

-- Cart contents (ongoing session 1001-2)
INSERT INTO cart(cid, sessionNo, pid, qty) VALUES
  (1001, 2, 2006, 1),
  (1001, 2, 2003, 2);

-- Past orders placed from prior sessions
INSERT INTO orders(ono, cid, sessionNo, odate, shipping_address) VALUES
  (3001, 1001, 1, '2025-10-25', '123 Maple St, Edmonton, AB'),
  (3002, 1002, 1, '2025-10-26', '55 River Rd, Calgary, AB');

INSERT INTO orderlines(ono, lineNo, pid, qty, uprice) VALUES
  (3001, 1, 2001, 1, 24.99),
  (3001, 2, 2003, 3, 9.95),
  (3002, 1, 2005, 1, 29.00),
  (3002, 2, 2004, 2, 5.25);
