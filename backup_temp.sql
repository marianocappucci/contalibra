DROP TABLE IF EXISTS `cajas`;
CREATE TABLE `cajas` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) NOT NULL,
  `saldo_inicial` decimal(10,2) NOT NULL DEFAULT 0.00,
  `saldo_final` decimal(10,2) NOT NULL DEFAULT 0.00,
  `abierta_por` int(11) NOT NULL,
  `cerrada_por` int(11) DEFAULT NULL,
  `fecha_apertura` datetime NOT NULL,
  `fecha_cierre` datetime DEFAULT NULL,
  `estado` enum('ABIERTA','CERRADA') NOT NULL DEFAULT 'ABIERTA',
  PRIMARY KEY (`id`),
  KEY `abierta_por` (`abierta_por`),
  KEY `cerrada_por` (`cerrada_por`),
  CONSTRAINT `cajas_ibfk_1` FOREIGN KEY (`abierta_por`) REFERENCES `usuarios` (`id`),
  CONSTRAINT `cajas_ibfk_2` FOREIGN KEY (`cerrada_por`) REFERENCES `usuarios` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `cajas` VALUES ('1','Caja principal','100000.00','500000.00','1','2','2025-11-20 16:31:31','2025-11-20 16:54:10','CERRADA');
INSERT INTO `cajas` VALUES ('2','Caja principal','234343.00','0.00','2','','2025-11-20 16:54:19','','ABIERTA');

DROP TABLE IF EXISTS `configuracion`;
CREATE TABLE `configuracion` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `nombre_fantasia` varchar(150) NOT NULL,
  `direccion` varchar(150) DEFAULT NULL,
  `telefono` varchar(100) DEFAULT NULL,
  `cuit` varchar(20) DEFAULT NULL,
  `punto_venta` varchar(10) DEFAULT NULL,
  `actualizado` datetime NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `configuracion` VALUES ('1','Compulibra','Malvinas 214','12312323','20-28993360-4','0001','2025-11-20 16:53:54');
INSERT INTO `configuracion` VALUES ('2','Mi Comercio','Dirección por defecto','1111-1111','00-00000000-0','0001','2025-11-20 16:53:16');

DROP TABLE IF EXISTS `listas_precios`;
CREATE TABLE `listas_precios` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) NOT NULL,
  `descripcion` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `listas_precios` VALUES ('1','General','Lista de precios general');

DROP TABLE IF EXISTS `productos`;
CREATE TABLE `productos` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(150) NOT NULL,
  `sku` varchar(50) NOT NULL,
  `precio` decimal(10,2) NOT NULL,
  `lista_precio_id` int(11) DEFAULT NULL,
  `stock` decimal(10,2) NOT NULL DEFAULT 0.00,
  `activo` tinyint(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`),
  KEY `lista_precio_id` (`lista_precio_id`),
  CONSTRAINT `productos_ibfk_1` FOREIGN KEY (`lista_precio_id`) REFERENCES `listas_precios` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `productos` VALUES ('1','Producto demo 1','P001','100.00','1','6.00','1');
INSERT INTO `productos` VALUES ('2','Producto demo 2','P002','250.00','1','0.00','1');
INSERT INTO `productos` VALUES ('3','Tostados','12312312312','2000.00','1','-4.00','1');
INSERT INTO `productos` VALUES ('4','coca cola','213','2009.00','1','0.00','1');

DROP TABLE IF EXISTS `roles`;
CREATE TABLE `roles` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(50) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `roles` VALUES ('1','Administrador');
INSERT INTO `roles` VALUES ('2','Vendedor');

DROP TABLE IF EXISTS `usuarios`;
CREATE TABLE `usuarios` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) NOT NULL,
  `username` varchar(50) NOT NULL,
  `password` varchar(255) NOT NULL,
  `rol_id` int(11) NOT NULL,
  `activo` tinyint(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  KEY `rol_id` (`rol_id`),
  CONSTRAINT `usuarios_ibfk_1` FOREIGN KEY (`rol_id`) REFERENCES `roles` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `usuarios` VALUES ('1','Administrador','admin','admin123','1','1');
INSERT INTO `usuarios` VALUES ('2','Mariano Cappucci','marianocappucci','LolaMora4520','1','1');

DROP TABLE IF EXISTS `ventas`;
CREATE TABLE `ventas` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `caja_id` int(11) NOT NULL,
  `usuario_id` int(11) NOT NULL,
  `cliente` varchar(150) NOT NULL,
  `subtotal` decimal(10,2) NOT NULL,
  `iva` decimal(10,2) NOT NULL,
  `total` decimal(10,2) NOT NULL,
  `fecha` datetime NOT NULL,
  `estado` varchar(20) NOT NULL,
  `tipo_comprobante` varchar(5) NOT NULL,
  `cae` varchar(20) DEFAULT NULL,
  `cae_vencimiento` varchar(8) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `caja_id` (`caja_id`),
  KEY `usuario_id` (`usuario_id`),
  CONSTRAINT `ventas_ibfk_1` FOREIGN KEY (`caja_id`) REFERENCES `cajas` (`id`),
  CONSTRAINT `ventas_ibfk_2` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `ventas` VALUES ('1','1','1','Consumidor Final','250.00','52.50','302.50','2025-11-20 16:32:14','FACTURADA','FA','SIM0000000001','20251130');
INSERT INTO `ventas` VALUES ('2','1','1','Consumidor Final','4500.00','945.00','5445.00','2025-11-20 16:33:50','FACTURADA','FC','SIM0000000002','20251130');
INSERT INTO `ventas` VALUES ('3','2','2','Consumidor Final','0.00','0.00','0.00','2025-11-20 18:40:23','FACTURADA','FA','SIM0000000003','20251130');
INSERT INTO `ventas` VALUES ('4','2','2','Consumidor Final','0.00','0.00','0.00','2025-11-20 18:40:31','FACTURADA','FA','SIM0000000004','20251130');
INSERT INTO `ventas` VALUES ('5','2','2','Consumidor Final','0.00','0.00','0.00','2025-11-20 18:46:25','FACTURADA','FA','SIM0000000005','20251130');
INSERT INTO `ventas` VALUES ('6','2','2','Consumidor Final','0.00','0.00','0.00','2025-11-20 18:47:35','FACTURADA','FA','SIM0000000006','20251130');
INSERT INTO `ventas` VALUES ('7','2','2','Consumidor Final','0.00','0.00','0.00','2025-11-20 18:47:48','FACTURADA','FA','SIM0000000007','20251130');
INSERT INTO `ventas` VALUES ('8','2','2','Consumidor Final','2000.00','420.00','2420.00','2025-11-20 18:55:37','FACTURADA','FA','SIM0000000008','20251130');
INSERT INTO `ventas` VALUES ('9','2','2','Consumidor Final','2000.00','420.00','2420.00','2025-11-20 19:10:19','FACTURADA','FA','SIM0000000009','20251130');
INSERT INTO `ventas` VALUES ('10','2','2','Consumidor Final','2009.00','421.89','2430.89','2025-11-20 19:11:41','FACTURADA','FA','SIM0000000010','20251130');
INSERT INTO `ventas` VALUES ('11','2','2','Consumidor Final','4109.00','862.89','4971.89','2025-11-20 19:54:13','FACTURADA','FA','SIM0000000011','20251130');
INSERT INTO `ventas` VALUES ('12','2','2','Consumidor Final','4009.00','841.89','4850.89','2025-11-20 20:13:12','FACTURADA','FA','SIM0000000012','20251130');
INSERT INTO `ventas` VALUES ('13','2','2','Consumidor Final','0.00','0.00','0.00','2025-11-20 20:20:59','FACTURADA','FA','SIM0000000013','20251130');
INSERT INTO `ventas` VALUES ('14','2','2','Consumidor Final','2359.00','495.39','2854.39','2025-11-20 20:22:59','FACTURADA','FA','SIM0000000014','20251130');
INSERT INTO `ventas` VALUES ('15','2','2','Consumidor Final','2359.00','495.39','2854.39','2025-11-20 20:23:10','FACTURADA','FA','SIM0000000015','20251130');
INSERT INTO `ventas` VALUES ('16','2','2','Consumidor Final','8109.00','1702.89','9811.89','2025-11-20 20:31:32','FACTURADA','FA','SIM0000000016','20251130');
INSERT INTO `ventas` VALUES ('17','2','2','Consumidor Final','8036.00','1687.56','9723.56','2025-11-21 09:39:25','FACTURADA','FA','SIM0000000017','20251201');

DROP TABLE IF EXISTS `ventas_detalle`;
CREATE TABLE `ventas_detalle` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `venta_id` int(11) NOT NULL,
  `producto_id` int(11) NOT NULL,
  `cantidad` decimal(10,2) NOT NULL,
  `precio_unitario` decimal(10,2) NOT NULL,
  `total` decimal(10,2) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `venta_id` (`venta_id`),
  KEY `producto_id` (`producto_id`),
  CONSTRAINT `ventas_detalle_ibfk_1` FOREIGN KEY (`venta_id`) REFERENCES `ventas` (`id`),
  CONSTRAINT `ventas_detalle_ibfk_2` FOREIGN KEY (`producto_id`) REFERENCES `productos` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=22 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `ventas_detalle` VALUES ('1','1','2','1.00','250.00','250.00');
INSERT INTO `ventas_detalle` VALUES ('2','2','3','2.00','2000.00','4000.00');
INSERT INTO `ventas_detalle` VALUES ('3','2','2','2.00','250.00','500.00');
INSERT INTO `ventas_detalle` VALUES ('4','8','3','1.00','2000.00','2000.00');
INSERT INTO `ventas_detalle` VALUES ('5','9','3','1.00','2000.00','2000.00');
INSERT INTO `ventas_detalle` VALUES ('6','10','4','1.00','2009.00','2009.00');
INSERT INTO `ventas_detalle` VALUES ('7','11','3','1.00','2000.00','2000.00');
INSERT INTO `ventas_detalle` VALUES ('8','11','4','1.00','2009.00','2009.00');
INSERT INTO `ventas_detalle` VALUES ('9','11','1','1.00','100.00','100.00');
INSERT INTO `ventas_detalle` VALUES ('10','12','4','1.00','2009.00','2009.00');
INSERT INTO `ventas_detalle` VALUES ('11','12','3','1.00','2000.00','2000.00');
INSERT INTO `ventas_detalle` VALUES ('12','14','4','1.00','2009.00','2009.00');
INSERT INTO `ventas_detalle` VALUES ('13','14','1','1.00','100.00','100.00');
INSERT INTO `ventas_detalle` VALUES ('14','14','2','1.00','250.00','250.00');
INSERT INTO `ventas_detalle` VALUES ('15','15','4','1.00','2009.00','2009.00');
INSERT INTO `ventas_detalle` VALUES ('16','15','1','1.00','100.00','100.00');
INSERT INTO `ventas_detalle` VALUES ('17','15','2','1.00','250.00','250.00');
INSERT INTO `ventas_detalle` VALUES ('18','16','4','1.00','2009.00','2009.00');
INSERT INTO `ventas_detalle` VALUES ('19','16','1','1.00','100.00','100.00');
INSERT INTO `ventas_detalle` VALUES ('20','16','3','3.00','2000.00','6000.00');
INSERT INTO `ventas_detalle` VALUES ('21','17','4','4.00','2009.00','8036.00');

