drop database if exists myblog;
create database myblog;
use myblog;
grant insert, select, update, delete on myblog.* to 'wang'@'localhost' identified by 'wang';

create table users (
  `id` varchar(50) not NULL,
  `name` varchar(50) not NULL,
  `password` varchar(50) not NULL,
  `email` varchar(50) not NULL,
  `admin` bool not NULL,
  `image` varchar(500) not NULL,
  `create_at` real not NULL,
  unique key `idx_email` (`email`),
  key `idx_create_at` (`create_at`),
  primary key (`id`)
)engine=innodb default charset=utf8;

create table blogs (
  `id` varchar(50) not NULL,
  `user_id` varchar(50) not null,
  `user_name` varchar(50) not NULL,
  `user_image` varchar(500) not NULL ,
  `name` varchar(50) not NULL ,
  `summary` varchar(200) not NULL ,
  `content` mediumtext not NULL ,
  `create_at` real not NULL ,
  key `idx_create_at` (`create_at`),
  primary key (`id`)
)engine=innodb default charset=utf8;

create table comments(
  `id` varchar(50) not null,
  `blog_id` varchar(50) not null,
  `user_id` varchar(50) not null,
  `user_name` varchar(50) not null,
  `user_image` varchar(500) not null,
  `content` mediumtext not null,
  `create_at` real not null,
  key `idx_create_at` (`create_at`),
  primary key (`id`)
)engine=innodb default charset=utf8;