<?php
@include('config.php');
$url = "http://api.openweathermap.org/data/2.5/weather?q=Chennai&appid=2de143494c0b295cca9337e1e96b00e0";

$json=file_get_contents($url);
$data=json_decode($json,true);

	//print_r($data);


/*
$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true );
// This is what solved the issue (Accepting gzip encoding)
curl_setopt($ch, CURLOPT_ENCODING, "gzip,deflate");     
$response = curl_exec($ch);
curl_close($ch);
echo $response;
*/


//Get current Temperature in Celsius
echo $data['main']['temp']."<br>";
//Get weather condition
echo $data['weather'][0]['main']."<br>";
//Get cloud percentage
echo $data['clouds']['all']."<br>";
//Get wind speed
echo $data['wind']['speed']."<br>";
?>