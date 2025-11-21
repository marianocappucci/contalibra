<?php
class Log{public function registrar($u,$n,$a,$m,$r=null){$c=new mysqli('localhost','root','','contadb');$c->set_charset('utf8');$ip=$_SERVER['REMOTE_ADDR'];$f=date('Y-m-d H:i:s');$stmt=$c->prepare('INSERT INTO logs(usuario_id,usuario_nombre,accion,modulo,registro_id,fecha,ip) VALUES(?,?,?,?,?,?,?)');$stmt->bind_param('isssiss',$u,$n,$a,$m,$r,$f,$ip);$stmt->execute();}}
?>