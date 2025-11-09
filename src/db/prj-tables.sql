-- Let's drop the tables in case they exist from previous runs
drop table if exists orderlines;
drop table if exists orders;
drop table if exists cart;
drop table if exists search;
drop table if exists viewedProduct;
drop table if exists sessions;
drop table if exists products;
drop table if exists customers;
drop table if exists users;

create table users (
  uid		int,
  pwd		text,
  role		text,
  primary key (uid)
);
create table customers (
  cid		int,
  name		text, 
  email		text,
  primary key (cid),
  foreign key (cid) references users
);
create table products (
  pid		int, 
  name		text, 
  category	text, 
  price		float, 
  stock_count	int, 
  descr		text,
  primary key (pid)
);
create table sessions (
  cid		int,
  sessionNo	int, 
  start_time	datetime, 
  end_time	datetime,
  primary key (cid, sessionNo),
  foreign key (cid) references customers on delete cascade
);
create table viewedProduct (
  cid		int, 
  sessionNo	int, 
  ts		timestamp, 
  pid		int,
  primary key (cid, sessionNo, ts),
  foreign key (cid, sessionNo) references sessions,
  foreign key (pid) references products
);
create table search (
  cid		int, 
  sessionNo	int, 
  ts		timestamp, 
  query		text,
  primary key (cid, sessionNo, ts),
  foreign key (cid, sessionNo) references sessions
);
create table cart (
  cid		int, 
  sessionNo	int, 
  pid		int,
  qty		int,
  primary key (cid, sessionNo, pid),
  foreign key (cid, sessionNo) references sessions,
  foreign key (pid) references products
);
create table orders (
  ono		int, 
  cid		int,
  sessionNo	int,
  odate		date, 
  shipping_address text,
  primary key (ono),
  foreign key (cid, sessionNo) references sessions
);
create table orderlines (
  ono		int, 
  lineNo	int, 
  pid		int, 
  qty		int, 
  uprice	float, 
  primary key (ono, lineNo),
  foreign key (ono) references orders on delete cascade
);

