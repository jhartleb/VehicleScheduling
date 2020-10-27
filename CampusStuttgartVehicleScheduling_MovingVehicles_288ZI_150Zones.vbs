
'Script is adjusted to Campus Scooter scenario with 150 zones and 288 time intervals

Dim Dist_ZI 
Dim Last_Abfahrten 
Dim Leer_Abfahrten 
Dim Last_Abfahrten_ZI 
Dim Leer_Abfahrten_ZI 
Dim Last_Fahrende_ZI 
Dim Leer_Fahrende_ZI 

Dim Dist
Dim i 'As Integer
Dim j 'As Integer
Dim ZI 'As Integer
Dim no_M_ZI_Last 'As Variant
Dim no_M_ZI_Leer 'As Variant
Dim NumDecimals

ReDim Dist_ZI(149, 149)
ReDim Last_Abfahrten(149, 149, 287)
ReDim Leer_Abfahrten(149, 149, 287)
ReDim Last_Abfahrten_ZI(149, 149)
ReDim Leer_Abfahrten_ZI(149, 149)
ReDim Last_Fahrende_ZI(149, 149)
ReDim Leer_Fahrende_ZI(149, 149)

NumDecimals = Visum.Net.AttValue("AV_NumOfDecimals")			' number of decimals for rounding

Dist_ZI = Visum.net.Matrices.ItemByKey(5001).GetValues	'distance matrix for distance between zones in time intervals

' writing time interval dependent demand into 3 dimensional array
For ZI = 0 To 287 ' for each time interval ZI
	no_M_ZI_Last = 6000 + ZI + 1
	Last_Abfahrten_ZI = Visum.net.Matrices.ItemByKey(no_M_ZI_Last).GetValues ' service trips (departures)
	no_M_ZI_Leer = 7000 + ZI + 1
	Leer_Abfahrten_ZI = Visum.net.Matrices.ItemByKey(no_M_ZI_Leer).GetValues ' empty trips (departures)
	For i = 0 To 149 'for each row
		For j = 0 To 149 'for each column
			Last_Abfahrten (i,j,ZI) = round(Last_Abfahrten_ZI (i,j),NumDecimals)
			Leer_Abfahrten (i,j,ZI) = round(Leer_Abfahrten_ZI (i,j),NumDecimals)
		Next
	Next
Next


'calculation for each time interval: how many moving vehicles
For ZI = 0 To 287
	
	For i = 0 To 149 'for each row
		For j = 0 To 149  'for each column
			' The number of vehicles driving in this time interval is the sum of the number of vehicles driving in this time interval and the number of vehicles that startet in previous time intervals and are still in motion (departure time interval <= current time interval < departure time interval + distance).
			Last_Fahrende_ZI(i,j) = 0
			Leer_Fahrende_ZI(i,j) = 0
			For Dist = 0 To (Dist_ZI(i,j)-1)	' Considers all time intervals (ZI) that lie between the current ZI (Dist = 0) and the ZI that lies so many ZIs (= Dist_ZI(i,j)-1) before the current one that a vehicle departing there reaches its destination in the current ZI.
				if (ZI - Dist) >= 0 Then		' ZIs that are before 00:00 a.m. are ignored: not closed vehicle schedule
					no_M_ZI_Last = ZI - Dist	' ZIs whose departures are added to moving vehicles
					Last_Fahrende_ZI (i,j) = round(Last_Fahrende_ZI (i,j) + Last_Abfahrten (i,j,no_M_ZI_Last),NumDecimals) ' moving vehicles in service
					if i = j Then		'No empty trips on the diagonal
						Leer_Fahrende_ZI (i,j) = 0
					Else
						no_M_ZI_Leer = ZI - Dist
						Leer_Fahrende_ZI (i,j) = round(Leer_Fahrende_ZI (i,j) + Leer_Abfahrten (i,j,no_M_ZI_Leer),NumDecimals) ' moving empty vehicles
					End If
				End If
			Next
		Next
	Next
	
	no_M_ZI_Last = 8000 + ZI + 1 'matrix number for moving vehicles in service in time interval ZI
	Call Visum.net.Matrices.ItemByKey(no_M_ZI_Last).SetValues(Last_Fahrende_ZI, False)
	no_M_ZI_Leer = 9000 + ZI + 1'matrix number for moving empty vehicles in time interval ZI
	Call Visum.net.Matrices.ItemByKey(no_M_ZI_Leer).SetValues(Leer_Fahrende_ZI, False)
Next


