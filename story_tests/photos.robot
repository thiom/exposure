*** Settings ***
Resource  resource.robot
Suite Setup      Open And Configure Browser
Suite Teardown   Close Browser
Test Setup       Reset Application And Log In

*** Keywords ***
Reset Application And Log In
    Reset Application
    Submit Registration  maija  ${PASSWORD}  ${PASSWORD}

*** Test Cases ***
User can add a photo with details and tags
    ${photo_id}=  Add Photo  Lake at dawn  tags=lake, morning  camera=Sony a7 IV
    ...           focal_length=24
    Get Text  .tag-rows  *=  \#lake
    Get Text  .tag-rows  *=  \#morning
    Click  text=done
    Get Url  ==  ${HOME_URL}/photo/${photo_id}
    Get Text  .photo-info  *=  Lake at dawn
    Get Text  .details  *=  Sony a7 IV
    Get Text  .details  *=  24 mm
    Get Text  .tags  *=  \#lake

User can edit the description of a photo
    ${photo_id}=  Add Photo  Lake at dawn
    Go To  ${HOME_URL}/photo/${photo_id}
    Click  .photo-info >> text=edit
    Fill Text  id=description  Lake at dusk
    Click  input[value="save"]
    Get Url  ==  ${HOME_URL}/photo/${photo_id}
    Get Text  .photo-info .description  ==  Lake at dusk

User can delete a photo
    ${photo_id}=  Add Photo
    Go To  ${HOME_URL}/edit_photo/${photo_id}
    Click  a >> text=delete photo
    Click  input[name="remove"]
    Get Url  ==  ${HOME_URL}/my_photos
    Get Text  .empty  *=  You have not added any photos yet
    Go To  ${HOME_URL}/photo/${photo_id}
    Get Text  h1  *=  Not Found

Search finds a photo and back returns to the results
    Add Photo  Foggy harbour  tags=sea
    Add Photo  Red barn
    Go To  ${HOME_URL}/
    Fill Text  id=query  sea
    Click  input[value="search"]
    Get Url  ==  ${HOME_URL}/search?query=sea
    Get Element Count  .photo-list img  ==  1
    Click  .photo-list a
    Get Text  .photo-info .description  ==  Foggy harbour
    Click  .photo-info >> text=back
    Get Url  ==  ${HOME_URL}/search?query=sea

Without photos the text is centered below the plus button
    Go To  ${HOME_URL}/my_photos
    ${latest}=  Get BoundingBox  .nav-left >> text=latest
    ${plus}=  Get BoundingBox  .add-new
    ${text}=  Get BoundingBox  .empty >> text=You have not added any photos yet.
    Should Be True  abs(${plus}[x] - ${latest}[x]) < 2
    Should Be True  ${plus}[y] + ${plus}[height] <= ${text}[y]
    Get Style  .empty  text-align  ==  center

Plus button on my photos is in line with latest and opens the add page
    Add Photo
    Go To  ${HOME_URL}/my_photos
    ${latest}=  Get BoundingBox  .nav-left >> text=latest
    ${plus}=  Get BoundingBox  .add-new
    ${photo}=  Get BoundingBox  .photo-list img
    Should Be True  abs(${plus}[x] - ${latest}[x]) < 2
    Should Be True  abs(${plus}[y] - ${photo}[y]) < 2
    Should Be True  ${plus}[x] + ${plus}[width] < ${photo}[x]
    Click  .add-new
    Get Url  ==  ${HOME_URL}/new_photo
