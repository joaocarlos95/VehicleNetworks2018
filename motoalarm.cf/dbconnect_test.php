<?php
$servername   = "localhost";
$database = "padeirin_RVmotoAlarm";
$username = "padeirin_RVmotoAlarm";
$password = "RVmotoAlarm";

// Create connection
$conn = new mysqli($servername, $username, $password);
// Check connection
if ($conn->connect_error) {
   die("Connection failed: " . $conn->connect_error);
}
  echo "Connected successfully";
?>