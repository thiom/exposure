*** Settings ***
Resource  resource.robot
Suite Setup      Open And Configure Browser
Suite Teardown   Close Browser
Test Setup       Reset Application

*** Test Cases ***
User can comment on another user's photo
    Submit Registration  maija  ${PASSWORD}  ${PASSWORD}
    ${photo_id}=  Add Photo
    Click  .nav-right >> text=log out
    Submit Registration  uolevi  ${PASSWORD}  ${PASSWORD}
    Go To  ${HOME_URL}/photo/${photo_id}
    Fill Text  id=content  Beautiful light
    Click  input[value="comment"]
    Get Url  ==  ${HOME_URL}/photo/${photo_id}?back=/#comments
    Get Text  .comment-meta  *=  uolevi
    Get Text  .comment-content  ==  Beautiful light

Logged out user is asked to log in to comment
    Submit Registration  maija  ${PASSWORD}  ${PASSWORD}
    ${photo_id}=  Add Photo
    Click  .nav-right >> text=log out
    Go To  ${HOME_URL}/photo/${photo_id}
    Get Element Count  id=content  ==  0
    Click  text=log in to comment
    Get Url  ==  ${LOGIN_URL}
