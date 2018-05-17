<?php 
	//getting the dboperation class
	require_once 'DbOperation.php';

	//function validating all the paramters are available
	//we will pass the required parameters to this function 
	function isTheseParametersAvailable($params){
		//assuming all parameters are available 
		$available = true; 
		$missingparams = ""; 
		
		foreach($params as $param){
			if(!isset($_POST[$param]) || strlen($_POST[$param])<=0){
				$available = false; 
				$missingparams = $missingparams . ", " . $param; 
			}
		}
		
		//if parameters are missing 
		if(!$available){
			$response = array(); 
			$response['error'] = true; 
			$response['message'] = 'Parameters ' . substr($missingparams, 1, strlen($missingparams)) . ' missing';
			
			//displaying error
			echo json_encode($response);
			
			//stopping further execution
			die();
		}
	}
	
	//an array to display response
	$response = array();
	
	//if it is an api call 
	//that means a get parameter named api call is set in the URL 
	//and with this parameter we are concluding that it is an api call
	if(isset($_GET['apicall'])){
		
		switch($_GET['apicall']){

			//the UPDATE operation
			case 'updateposition':
				isTheseParametersAvailable(array('stationID','eventPositionLatitude','eventPositionLongitude','eventTime','eventSpeed','eventPositionHeading'));
				$db = new DbOperation();
				$result = $db->updatePosition(
					$_POST['stationID'],
					$_POST['eventPositionLatitude'],
					$_POST['eventPositionLongitude'],
					$_POST['eventTime'],
					$_POST['eventSpeed'],
					$_POST['eventPositionHeading']
				);
				
				if($result){
					$response['error'] = false; 
					$response['message'] = 'Position updated successfully';
					//$response['cars'] = $db->getCars();
				}else{
					$response['error'] = true; 
					$response['message'] = 'Some error occurred please try again';
				}
			break; 
			
		}
		
	}else{
		//if it is not api call 
		//pushing appropriate values to response array 
		$response['error'] = true; 
		$response['message'] = 'Invalid API Call';
	}
	

	//displaying the response in json structure 
	$json = json_encode($response);
	
	if ($json)
    	echo $json;
	else
    	echo json_last_error_msg();

