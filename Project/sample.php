<?php
$con=mysql_connect("localhost","root","");
mysql_select_db("ranjith",$con);
$sql=mysql_query("INSERT INTO datas(name,age,address,phoneno,occuipation VALUES('".$_post['name']."','".$_POST['age']."','".$_post['address']."','".$_POST['phoneno']."','".$_POST['occuipation']."')");
?>
<html>
<body>
<table border="1">
<form action="sample.php" method="post">
<tr><td>
Name:</td><td><input type="text" name="name" required></td></tr>
<tr><td>
Age:</td><td><input type="number" name="age" required></td></tr>
<tr><td>
Address:</td><td><input type="text" name="address" required></td></tr>
<tr><td>
phone_No:</td><td><input type="number" name="phoneno" required></td></tr>
<tr><td>
Occuipation:</td><td><input type="text" name="occuipation"></td></tr>
</form>
</table>
<table border="1">
<form>
<tr><td>Name</td>
<td>Age</td>
<td>Address</td>
<td>Phone_No</td>
<td>occuipation</td>
</tr>
</table>
</body>
</html>
<?php
$sql=mysql_query("select * from datas");
while($sql

?>