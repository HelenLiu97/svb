/*
Navicat MySQL Data Transfer

Source Server         : 127.0.0.1
Source Server Version : 50643
Source Host           : localhost:3306
Source Database       : svb

Target Server Type    : MYSQL
Target Server Version : 50643
File Encoding         : 65001

Date: 2020-02-21 18:12:53
*/

SET FOREIGN_KEY_CHECKS=0;

-- ----------------------------
-- Table structure for admin
-- ----------------------------
DROP TABLE IF EXISTS `admin`;
CREATE TABLE `admin` (
  `id` mediumint(11) NOT NULL AUTO_INCREMENT,
  `account` varchar(255) DEFAULT NULL,
  `password` varchar(255) DEFAULT NULL,
  `name` varchar(255) DEFAULT NULL,
  `balance` float DEFAULT NULL,
  `ex_change` float DEFAULT '0',
  `ex_range` float DEFAULT '0',
  `hand` float DEFAULT '0',
  `top_push` varchar(255) DEFAULT NULL,
  `dollar_hand` float DEFAULT NULL,
  `notice` text,
  `up_remain_time` datetime DEFAULT NULL,
  `set_change` varchar(10) DEFAULT NULL,
  `set_range` varchar(10) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Records of admin
-- ----------------------------
INSERT INTO `admin` VALUES ('1', 'baocui', 'baocui123', '大龙', null, '7.999', '0.03', '0.05', '{\"liuixiao\": \"2404052713@qq.com\"}', '10000', '《影响教师一生的100个好习惯》一书，从教师的教育习惯、教学习惯、学习习惯、生活习惯、行为习惯五个方面，归纳出100个好习惯，它是一本系统研究教师习惯的著作，必将为广大教师专业成长和专业发展提供指导性的可借鉴的范著。\n\n　　在影响教师100个好习惯之一，教育习惯篇，做一名有智慧的教育者中指出：教育本身是一种智慧，而教师作为教育者，更需要拥有教育智慧，教师的教育智慧从哪里来，从良好的习惯中来，当教师就要当一个有口叫位的教师，有品位的教师。犹如醇美的米酒，让人回味，沁人心脾。!@#2020-02-21 15:57:07', '2020-02-21 18:12:29', '7.0', '0.3');

-- ----------------------------
-- Table structure for bank_info
-- ----------------------------
DROP TABLE IF EXISTS `bank_info`;
CREATE TABLE `bank_info` (
  `id` mediumint(11) NOT NULL AUTO_INCREMENT,
  `bank_name` char(255) NOT NULL,
  `bank_number` char(255) NOT NULL,
  `bank_address` char(255) NOT NULL,
  `day_money` float(11,2) NOT NULL DEFAULT '0.00',
  `money` decimal(10,2) NOT NULL DEFAULT '0.00',
  `status` int(11) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Records of bank_info
-- ----------------------------
INSERT INTO `bank_info` VALUES ('1', '郭炳安', '6222032019002206643', '中国工商揭阳揭西棉湖支行', '2.00', '616030.87', '0');
INSERT INTO `bank_info` VALUES ('2', '谢集波', '6222032019002206387', '工行揭阳揭西棉湖支行', '2.00', '580000.31', '0');
INSERT INTO `bank_info` VALUES ('3', '郭美芬', '6222032019002206320', '工行揭阳揭西棉湖支行', '845.04', '639599.87', '2');
INSERT INTO `bank_info` VALUES ('4', '孙玥敏', '6217004220054044668', '中国建设银行股份有限公司西安曲江支行', '1.00', '423108.64', '0');
INSERT INTO `bank_info` VALUES ('5', '孙玥敏', '6217853600019933745', '中国银行西安方新村支行', '0.00', '215102.89', '0');

-- ----------------------------
-- Table structure for card_info
-- ----------------------------
DROP TABLE IF EXISTS `card_info`;
CREATE TABLE `card_info` (
  `id` mediumint(11) NOT NULL AUTO_INCREMENT,
  `card_id` int(11) DEFAULT NULL,
  `card_number` varchar(255) DEFAULT NULL,
  `expiry` varchar(255) DEFAULT NULL,
  `cvc` varchar(255) DEFAULT NULL,
  `last4` varchar(255) DEFAULT NULL,
  `valid_start_on` date DEFAULT NULL,
  `valid_end_on` date DEFAULT NULL,
  `label` varchar(255) DEFAULT NULL,
  `status` varchar(255) DEFAULT NULL,
  `balance` float(11,2) NOT NULL DEFAULT '0.00',
  `user_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `card_info_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `user_info` (`id`) ON DELETE CASCADE ON UPDATE NO ACTION
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Records of card_info
-- ----------------------------
INSERT INTO `card_info` VALUES ('1', '38152080', '5563381670349044', '2022-02', '221', '9044', '2020-02-18', '2023-02-19', null, 'T', '11.00', '1');
INSERT INTO `card_info` VALUES ('2', '38126156', '5563388829521290', '2022-02', '950', '1290', '2020-02-18', '2023-02-19', '消费了的', 'T', '12.00', '1');

-- ----------------------------
-- Table structure for card_trans
-- ----------------------------
DROP TABLE IF EXISTS `card_trans`;
CREATE TABLE `card_trans` (
  `id` mediumint(11) NOT NULL AUTO_INCREMENT,
  `card_number` varchar(255) DEFAULT NULL,
  `acquirer_ica` varchar(255) DEFAULT NULL,
  `approval_code` varchar(255) DEFAULT NULL,
  `billing_amount` float(255,2) DEFAULT NULL,
  `billing_currency` varchar(255) DEFAULT NULL,
  `issuer_reponse` varchar(255) DEFAULT NULL,
  `mcc` varchar(255) DEFAULT NULL,
  `mcc_description` varchar(255) DEFAULT NULL,
  `merchant_amount` float(255,2) DEFAULT NULL,
  `merchant_currency` varchar(255) DEFAULT NULL,
  `merchant_id` varchar(255) DEFAULT NULL,
  `merchant_name` varchar(255) DEFAULT NULL,
  `transaction_date_time` varchar(255) DEFAULT NULL,
  `transaction_type` varchar(255) DEFAULT NULL,
  `vcn_response` varchar(255) DEFAULT NULL,
  `card_id` int(11) DEFAULT NULL,
  `status` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Records of card_trans
-- ----------------------------
INSERT INTO `card_trans` VALUES ('1', '5563388829521290', '003286', 'None', '10.00', 'USD', 'Decline - Insufficient funds/over credit limit', '5942', 'BOOK STORES', '10.00', 'USD', '784959000762203', 'Amazon.com             Amzn.com/bill WA ', '2020-02-19T15:11:16.000Z', 'Authorization Advice', 'Decline - total_card_amount', '38126156', 'F');
INSERT INTO `card_trans` VALUES ('2', '5563388829521290', '003286', '018787', '5.00', 'USD', 'Approved', '5942', 'BOOK STORES', '5.00', 'USD', '784959000762203', 'Amazon.com             Amzn.com/bill WA ', '2020-02-19T05:15:21.000Z', 'Authorization Advice', 'Valid', '38126156', 'T');

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
  `card_price` float DEFAULT NULL,
  `note` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=latin1;

-- ----------------------------
-- Records of middle
-- ----------------------------

-- ----------------------------
-- Table structure for middle_money
-- ----------------------------
DROP TABLE IF EXISTS `middle_money`;
CREATE TABLE `middle_money` (
  `id` mediumint(11) NOT NULL AUTO_INCREMENT,
  `middle_id` int(11) DEFAULT NULL,
  `start_time` datetime DEFAULT NULL,
  `end_time` datetime DEFAULT NULL,
  `card_num` int(11) DEFAULT NULL,
  `create_price` float(11,2) DEFAULT NULL,
  `sum_money` float(11,2) DEFAULT NULL,
  `create_time` datetime DEFAULT NULL,
  `pay_status` varchar(255) DEFAULT NULL,
  `pay_time` datetime DEFAULT NULL,
  `detail` text,
  `note` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `middle_id` (`middle_id`) USING BTREE,
  CONSTRAINT `middle_money_ibfk_1` FOREIGN KEY (`middle_id`) REFERENCES `middle` (`id`) ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- ----------------------------
-- Records of middle_money
-- ----------------------------

-- ----------------------------
-- Table structure for pay_log
-- ----------------------------
DROP TABLE IF EXISTS `pay_log`;
CREATE TABLE `pay_log` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `pay_time` datetime DEFAULT NULL,
  `pay_money` float(255,3) DEFAULT NULL,
  `top_money` float(255,2) DEFAULT NULL,
  `ver_code` varchar(255) DEFAULT NULL,
  `status` varchar(255) DEFAULT NULL,
  `ver_time` datetime DEFAULT NULL,
  `phone` varchar(255) DEFAULT NULL,
  `url` varchar(255) DEFAULT '',
  `account_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `account_id` (`account_id`) USING BTREE,
  CONSTRAINT `pay_log_ibfk_1` FOREIGN KEY (`account_id`) REFERENCES `user_info` (`id`) ON DELETE CASCADE ON UPDATE NO ACTION
) ENGINE=InnoDB AUTO_INCREMENT=313 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Records of pay_log
-- ----------------------------

-- ----------------------------
-- Table structure for qr_code
-- ----------------------------
DROP TABLE IF EXISTS `qr_code`;
CREATE TABLE `qr_code` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `url` varchar(255) DEFAULT NULL,
  `up_date` datetime DEFAULT NULL,
  `top_money` int(11) DEFAULT '0',
  `status` int(11) DEFAULT '0',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Records of qr_code
-- ----------------------------
INSERT INTO `qr_code` VALUES ('3', 'https://i.loli.net/2019/12/02/gchIUuisAm3Sjvy.png', '2019-12-02 14:45:17', '743', '0');
INSERT INTO `qr_code` VALUES ('4', 'https://i.loli.net/2019/12/02/yK6N8LuiQ9DazJb.png', '2019-12-02 14:45:33', '0', '0');
INSERT INTO `qr_code` VALUES ('5', 'https://i.loli.net/2019/12/02/8WO1SnGUZgXCMhQ.png', '2019-12-02 14:45:45', '0', '0');
INSERT INTO `qr_code` VALUES ('6', 'https://i.loli.net/2020/02/21/CTsc6HBu9KFMVSd.jpg', '2020-02-21 16:59:16', '0', '0');

-- ----------------------------
-- Table structure for recharge_account
-- ----------------------------
DROP TABLE IF EXISTS `recharge_account`;
CREATE TABLE `recharge_account` (
  `id` mediumint(11) NOT NULL AUTO_INCREMENT,
  `name` char(255) NOT NULL,
  `username` char(255) NOT NULL,
  `password` char(255) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Records of recharge_account
-- ----------------------------
INSERT INTO `recharge_account` VALUES ('1', '特', 'test3', 'trybest');
INSERT INTO `recharge_account` VALUES ('2', '刘晓', 'liuda', 'liuda123');

-- ----------------------------
-- Table structure for top_up
-- ----------------------------
DROP TABLE IF EXISTS `top_up`;
CREATE TABLE `top_up` (
  `id` mediumint(11) NOT NULL AUTO_INCREMENT,
  `pay_num` varchar(225) DEFAULT NULL,
  `time` datetime DEFAULT NULL,
  `money` float DEFAULT NULL,
  `before_balance` float DEFAULT NULL,
  `balance` float DEFAULT NULL,
  `user_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `account_id` (`user_id`) USING BTREE,
  CONSTRAINT `top_up_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `user_info` (`id`) ON DELETE CASCADE ON UPDATE NO ACTION
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Records of top_up
-- ----------------------------
INSERT INTO `top_up` VALUES ('1', '202002211801452b2de', '2020-02-21 18:01:45', '0', '0', '0', '1');

-- ----------------------------
-- Table structure for user_info
-- ----------------------------
DROP TABLE IF EXISTS `user_info`;
CREATE TABLE `user_info` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `account` varchar(255) CHARACTER SET utf8 DEFAULT NULL,
  `password` varchar(255) CHARACTER SET utf8 DEFAULT NULL,
  `phone_num` varchar(255) DEFAULT '',
  `name` varchar(255) CHARACTER SET utf8 DEFAULT NULL,
  `create_price` float(11,2) DEFAULT '0.00',
  `min_top` int(11) DEFAULT NULL,
  `max_top` int(11) DEFAULT '3000',
  `balance` float(11,2) DEFAULT '0.00',
  `sum_balance` float(11,2) DEFAULT '0.00',
  `last_login_time` datetime DEFAULT NULL,
  `middle_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `middle_id` (`middle_id`) USING BTREE,
  CONSTRAINT `user_info_ibfk_1` FOREIGN KEY (`middle_id`) REFERENCES `middle` (`id`) ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=latin1;

-- ----------------------------
-- Records of user_info
-- ----------------------------
INSERT INTO `user_info` VALUES ('1', 'helen', 'trybest123', '18902222484', 'Helen', '5.00', '1', '30000', '0.00', '0.00', '2020-02-21 18:03:08', null);

-- ----------------------------
-- Table structure for user_trans
-- ----------------------------
DROP TABLE IF EXISTS `user_trans`;
CREATE TABLE `user_trans` (
  `id` mediumint(11) NOT NULL AUTO_INCREMENT,
  `do_date` datetime DEFAULT NULL,
  `trans_type` varchar(255) DEFAULT NULL,
  `do_type` varchar(255) DEFAULT NULL,
  `card_no` varchar(255) DEFAULT NULL,
  `do_money` float(255,2) DEFAULT NULL,
  `before_balance` float(255,2) DEFAULT NULL,
  `balance` float(255,2) DEFAULT NULL,
  `user_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=43 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Records of user_trans
-- ----------------------------
INSERT INTO `user_trans` VALUES ('1', '2020-02-04 17:08:28', '支出', '开卡', '5563385290078354', '12.00', '100.00', '100.00', '292');
INSERT INTO `user_trans` VALUES ('2', '2020-02-04 17:14:09', '支出', '开卡', '5563389399584973', '12.00', '88.00', '76.00', '292');
INSERT INTO `user_trans` VALUES ('3', '2020-02-04 17:14:09', '支出', '充值', '5563389399584973', '10.00', '76.00', '66.00', '292');
INSERT INTO `user_trans` VALUES ('4', '2020-02-04 17:15:29', '支出', '开卡', '5563385027615684', '12.00', '66.00', '54.00', '292');
INSERT INTO `user_trans` VALUES ('5', '2020-02-04 17:15:29', '支出', '充值', '5563385027615684', '12.00', '54.00', '42.00', '292');
INSERT INTO `user_trans` VALUES ('6', '2020-02-04 19:26:43', '支出', '充值', '5563385290078354', '1.00', '42.00', '41.00', '292');
INSERT INTO `user_trans` VALUES ('7', '2020-02-04 19:27:28', '支出', '充值', '5563385290078354', '1.00', '41.00', '40.00', '292');
INSERT INTO `user_trans` VALUES ('8', '2020-02-04 19:31:17', '支出', '充值', '5563385290078354', '2.00', '40.00', '38.00', '292');
INSERT INTO `user_trans` VALUES ('9', '2020-02-04 19:32:21', '支出', '充值', '5563385290078354', '2.00', '38.00', '36.00', '292');
INSERT INTO `user_trans` VALUES ('10', '2020-02-04 19:33:19', '支出', '充值', '5563385290078354', '3.00', '36.00', '33.00', '292');
INSERT INTO `user_trans` VALUES ('11', '2020-02-05 12:05:11', '支出', '充值', '5563385290078354', '3.00', '33.00', '30.00', '292');
INSERT INTO `user_trans` VALUES ('12', '2020-02-05 15:15:36', '支出', '充值', '5563389399584973', '1.00', '30.00', '29.00', '292');
INSERT INTO `user_trans` VALUES ('13', '2020-02-05 15:17:05', '支出', '充值', '5563389399584973', '1.00', '29.00', '28.00', '292');
INSERT INTO `user_trans` VALUES ('14', '2020-02-05 15:30:58', '支出', '充值', '5563389399584973', '1.00', '28.00', '27.00', '292');
INSERT INTO `user_trans` VALUES ('15', '2020-02-05 15:32:21', '支出', '充值', '5563389399584973', '1.00', '27.00', '26.00', '292');
INSERT INTO `user_trans` VALUES ('16', '2020-02-05 15:33:50', '支出', '充值', '5563389399584973', '1.00', '26.00', '25.00', '292');
INSERT INTO `user_trans` VALUES ('17', '2020-02-05 15:35:00', '支出', '充值', '5563389399584973', '1.00', '25.00', '24.00', '292');
INSERT INTO `user_trans` VALUES ('18', '2020-02-05 15:47:53', '收入', '转移退款', '5563389399584973', '1.00', '24.00', '25.00', '292');
INSERT INTO `user_trans` VALUES ('19', '2020-02-05 15:50:31', '收入', '转移退款', '5563389399584973', '17.99', '25.00', '42.99', '292');
INSERT INTO `user_trans` VALUES ('20', '2020-02-05 16:23:01', '收入', '注销', '5563389399584973', '0.01', '42.99', '43.00', '292');
INSERT INTO `user_trans` VALUES ('21', '2020-02-05 16:25:45', '收入', '注销', '5563385290078354', '55.00', '43.00', '98.00', '292');
INSERT INTO `user_trans` VALUES ('22', '2020-02-05 16:58:38', '支出', '充值', '5563385027615684', '88.00', '98.00', '10.00', '292');
INSERT INTO `user_trans` VALUES ('23', '2020-02-05 19:09:14', '支出', '开卡', '5563387919435312', '12.00', '40.00', '28.00', '292');
INSERT INTO `user_trans` VALUES ('24', '2020-02-05 19:09:14', '支出', '充值', '5563387919435312', '10.00', '28.00', '18.00', '292');
INSERT INTO `user_trans` VALUES ('25', '2020-02-06 11:42:56', '收入', '退款', '5563385027615684', '10.00', '18.00', '28.00', '292');
INSERT INTO `user_trans` VALUES ('26', '2020-02-06 15:43:00', '收入', '注销', '5563387919435312', '10.00', '28.00', '38.00', '292');
INSERT INTO `user_trans` VALUES ('27', '2020-02-10 12:20:02', '支出', '系统扣费', '0', '10.00', '58.00', '48.00', '292');
INSERT INTO `user_trans` VALUES ('28', '2020-02-10 15:05:14', '充值', '支出', '0', '0.00', '0.00', '0.00', '0');
INSERT INTO `user_trans` VALUES ('29', '2020-02-10 15:06:53', '充值', '支出', '0', '0.00', '0.00', '0.00', '0');
INSERT INTO `user_trans` VALUES ('30', '2020-02-10 15:07:24', '充值', '支出', '0', '0.00', '0.00', '0.00', '293');
INSERT INTO `user_trans` VALUES ('31', '2020-02-19 12:24:25', '支出', '充值', '5563388829521290', '1.00', '260.00', '259.00', '292');
INSERT INTO `user_trans` VALUES ('32', '2020-02-19 16:48:40', '支出', '开卡', '5563381670349044', '18.00', '259.00', '241.00', '292');
INSERT INTO `user_trans` VALUES ('33', '2020-02-19 16:48:40', '支出', '充值', '5563381670349044', '30.00', '241.00', '211.00', '292');
INSERT INTO `user_trans` VALUES ('34', '2020-02-19 16:49:09', '支出', '充值', '5563381670349044', '1.00', '211.00', '210.00', '292');
INSERT INTO `user_trans` VALUES ('35', '2020-02-19 16:49:36', '收入', '退款', '5563381670349044', '20.00', '210.00', '230.00', '292');
INSERT INTO `user_trans` VALUES ('36', '2020-02-19 17:58:30', '支出', '充值', '5563388829521290', '5.00', '230.00', '225.00', '292');
INSERT INTO `user_trans` VALUES ('37', '2020-02-19 18:03:21', '支出', '充值', '5563388829521290', '5.00', '225.00', '220.00', '292');
INSERT INTO `user_trans` VALUES ('38', '2020-02-19 18:07:03', '收入', '退款', '5563388829521290', '10.00', '220.00', '230.00', '292');
INSERT INTO `user_trans` VALUES ('39', '2020-02-20 11:04:32', '支出', '充值', '5563388829521290', '1.00', '230.00', '229.00', '292');
INSERT INTO `user_trans` VALUES ('40', '2020-02-20 11:05:11', '收入', '退款', '5563388829521290', '4.00', '229.00', '233.00', '292');
INSERT INTO `user_trans` VALUES ('41', '2020-02-21 16:04:13', '支出', '充值', '5563388829521290', '10.00', '333.00', '323.00', '292');
INSERT INTO `user_trans` VALUES ('42', '2020-02-21 18:01:45', '充值', '支出', '0', '0.00', '0.00', '0.00', '1');

-- ----------------------------
-- Table structure for verify_account
-- ----------------------------
DROP TABLE IF EXISTS `verify_account`;
CREATE TABLE `verify_account` (
  `u_name` varchar(255) DEFAULT NULL,
  `u_account` varchar(255) DEFAULT NULL,
  `u_password` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- ----------------------------
-- Records of verify_account
-- ----------------------------
INSERT INTO `verify_account` VALUES ('宝翠一号', 'NEWTIME', 'trybest321');

-- ----------------------------
-- Table structure for vice_user
-- ----------------------------
DROP TABLE IF EXISTS `vice_user`;
CREATE TABLE `vice_user` (
  `id` mediumint(11) NOT NULL AUTO_INCREMENT,
  `v_account` varchar(255) DEFAULT NULL,
  `v_password` varchar(255) DEFAULT NULL,
  `c_card` varchar(255) DEFAULT NULL,
  `top_up` varchar(255) DEFAULT NULL,
  `refund` varchar(255) DEFAULT NULL,
  `del_card` varchar(255) DEFAULT NULL,
  `up_label` varchar(255) DEFAULT NULL,
  `user_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `v_account` (`v_account`) USING BTREE,
  KEY `account_id` (`user_id`) USING BTREE,
  CONSTRAINT `vice_user_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `user_info` (`id`) ON DELETE CASCADE ON UPDATE NO ACTION
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- ----------------------------
-- Records of vice_user
-- ----------------------------
