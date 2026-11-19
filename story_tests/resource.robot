*** Settings ***
Library  Browser

*** Variables ***
${SERVER}        localhost:5002
${DELAY}         500ms
${HOME_URL}      http://${SERVER}
${LOGIN_URL}     http://${SERVER}/login
${REGISTER_URL}  http://${SERVER}/register
${RESET_URL}     http://${SERVER}/reset_db
${BROWSER}       chromium
${HEADLESS}      false
${PASSWORD}      secret-password
${PHOTO}         ${CURDIR}/photo.jpg

*** Keywords ***
Open And Configure Browser
    IF  $HEADLESS == 'true'
        New Browser  browser=${BROWSER}  headless=True
    ELSE
        New Browser  browser=${BROWSER}  headless=False  slowMo=${DELAY}
    END
    New Context
    New Page  about:blank

Reset Application
    Go To  ${RESET_URL}

Submit Registration
    [Arguments]  ${username}  ${password}  ${confirmation}
    Go To  ${REGISTER_URL}
    Fill Text  id=username  ${username}
    Fill Text  id=password1  ${password}
    Fill Text  id=password2  ${confirmation}
    Click  input[type="submit"]

Submit Login
    [Arguments]  ${username}  ${password}
    Go To  ${LOGIN_URL}
    Fill Text  id=username  ${username}
    Fill Text  id=password  ${password}
    Click  input[type="submit"]

Create User
    [Arguments]  ${username}  ${password}=${PASSWORD}
    Submit Registration  ${username}  ${password}  ${password}
    Click  text=log out

User Should Be Logged In
    Get Element Count  .nav-right >> text=log out  ==  1
    Get Element Count  .nav-right >> text=my photos  ==  1

User Should Not Be Logged In
    Get Element Count  .nav-right >> text=log out  ==  0

Add Photo
    [Documentation]  Adds a photo and returns its id. Leaves the browser on the tag page.
    [Arguments]  ${description}=Foggy morning  ${tags}=${EMPTY}  ${camera}=${EMPTY}
    ...          ${focal_length}=${EMPTY}
    Go To  ${HOME_URL}/new_photo
    Upload File By Selector  id=image  ${PHOTO}
    Fill Text  id=description  ${description}
    Fill Text  id=tags  ${tags}
    Fill Text  id=camera  ${camera}
    Fill Text  id=focal_length  ${focal_length}
    Click  input[type="submit"]
    Get Url  matches  ${HOME_URL}/tags/\\d+$
    ${url}=  Get Url
    ${photo_id}=  Evaluate  $url.split("/")[-1]
    RETURN  ${photo_id}
