<?php
 
class DbOperation
{
    //Database connection link
    private $con;
 
    //Class constructor
    function __construct()
    {
        //Getting the DbConnect.php file
        require_once dirname(__FILE__) . '/DbConnect.php';
 
        //Creating a DbConnect object to connect to the database
        $db = new DbConnect();
 
        //Initializing our connection link of this class
        //by calling the method connect of DbConnect class
        $this->con = $db->connect();
    }
	
	/*
	* The update operation
	* When this method is called the record with the given id is updated with the new given values
	*/
	function updatePosition($stationID, $eventPositionLatitude,$eventPositionLongitude, $eventTime, $eventSpeed, $eventPositionHeading ){
		//Input Validation
		//if((preg_match('/^[a-z0-9\_\ ]+$/i',$comment)) and (preg_match('/^[a-z0-9\_\ ]+$/i',$phone)))


		//eventPosition

		$query = "INSERT INTO markers SET name = '{$stationID}',lat  = '{$eventPositionLatitude}', lng   = '{$eventPositionLongitude}' , speed = '{$eventSpeed}', timestamp = '{$eventTime}', direction = '{$eventPositionHeading}' ";
		$stmt = $this->con->prepare($query);

		if($stmt->execute()){
			return true; 
		}else{
			return false; 	
		}
	
	}

}