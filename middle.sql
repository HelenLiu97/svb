/*
Navicat MySQL Data Transfer

Source Server         : 127.0.0.1
Source Server Version : 50643
Source Host           : localhost:3306
Source Database       : svb

Target Server Type    : MYSQL
Target Server Version : 50643
File Encoding         : 65001

Date: 2020-03-12 16:23:49
*/

SET FOREIGN_KEY_CHECKS=0;

-- ----------------------------
-- Table structure for middle
-- ----------------------------
DROP TABLE IF EXISTS `middle`;
CREATE TABLE `middle` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `account` varchar(255) CHARACTER SET utf8 DEFAULT NULL,
  `password` varchar(255) CHARACTER SET utf8 DEFAULT NULL,
  `name` varchar(255) CHARACTER SET utf8 DEFAULT NULL,
  `phone_num` varchar(255) CHARACTER SET utf8 DEFAULT NULL,
  `price_one` float(11,2) DEFAULT NULL,
  `price_two` float(11,2) DEFAULT NULL,
  `price_three` float(11,2) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=latin1;
