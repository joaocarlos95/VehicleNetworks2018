<?php

require("phpsqlajax_dbinfo.php");


function parseToXML($htmlStr)
{
$xmlStr=str_replace('<','&lt;',$htmlStr);
$xmlStr=str_replace('>','&gt;',$xmlStr);
$xmlStr=str_replace('"','&quot;',$xmlStr);
$xmlStr=str_replace("'",'&#39;',$xmlStr);
$xmlStr=str_replace("&",'&amp;',$xmlStr);
return $xmlStr;
}

//connecting to mysql database
$con = new mysqli($servername, $username, $password, $database);
//Checking if any error occured while connecting
if (mysqli_connect_errno()) {
	echo "Failed to connect to MySQL: " . mysqli_connect_error();
} 


header("Content-type: text/xml");

// Start XML file, echo parent node
echo '<markers>';


//run the query
$result = mysqli_query($con, "SELECT * FROM markers WHERE 1")
    or die (mysqli_error($dbh));

while ($row = mysqli_fetch_array($result))
{
     
	echo '<marker ';
	  	echo 'name="' . parseToXML($row['name']) . '" ';
	  	echo 'address="' . parseToXML($row['address']) . '" ';
	  	echo 'lat="' . $row['lat'] . '" ';
	  	echo 'lng="' . $row['lng'] . '" ';
	  	echo 'type="' . $row['type'] . '" ';
	  	echo 'speed="' . $row['speed'] . '" ';
	  	echo 'timestamp="' . $row['timestamp'] . '" ';
	  	echo 'direction="' . $row['direction'] . '" ';
  	echo '/>';

}


// End XML file
echo '</markers>';

?>