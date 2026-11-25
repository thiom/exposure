*** Settings ***
Resource  resource.robot
Suite Setup      Open And Configure Browser
Suite Teardown   Close Browser
Test Setup       Reset Application

*** Test Cases ***
User can register
    Submit Registration  maija  ${PASSWORD}  ${PASSWORD}
    Get Url  ==  ${HOME_URL}/
    User Should Be Logged In

Registering fails with a username that is in use
    Create User  maija
    Submit Registration  maija  ${PASSWORD}  ${PASSWORD}
    Get Text  .flash  *=  Username already in use, pick another one
    User Should Not Be Logged In
    Get Property  id=username  value  ==  maija
    Get Property  id=password1  value  ==  ${PASSWORD}
    Get Property  id=password2  value  ==  ${PASSWORD}

Registering fails when the passwords do not match and the inputs are kept
    Submit Registration  maija  ${PASSWORD}  ${PASSWORD}x
    Get Text  .flash  *=  Passwords do not match
    User Should Not Be Logged In
    Get Property  id=username  value  ==  maija
    Get Property  id=password1  value  ==  ${PASSWORD}
    Get Property  id=password2  value  ==  ${PASSWORD}x

Login fails with a wrong password
    Create User  maija
    Submit Login  maija  wrong-password
    Get Text  .flash  *=  Wrong username or password
    User Should Not Be Logged In
    Get Property  id=username  value  ==  maija
    Get Property  id=password  value  ==  wrong-password

Sign up link in the top bar opens the registration page
    Go To  ${HOME_URL}/
    ${sign_up}=  Get BoundingBox  .nav-right >> text=sign up
    ${log_in}=  Get BoundingBox  .nav-right >> text=log in
    Should Be True  ${sign_up}[x] + ${sign_up}[width] < ${log_in}[x]
    Click  .nav-right >> text=sign up
    Get Url  ==  ${REGISTER_URL}
    Submit Registration  maija  ${PASSWORD}  ${PASSWORD}
    User Should Be Logged In
    Get Element Count  .nav-right >> text=sign up  ==  0

Go to log in button is right of the create account button
    Go To  ${REGISTER_URL}
    ${create}=  Get BoundingBox  input[value="create account"]
    ${log_in}=  Get BoundingBox  a >> text=go to log in
    Should Be True  ${create}[x] + ${create}[width] + 10 < ${log_in}[x]
    Should Be True  abs(${create}[y] - ${log_in}[y]) < 1
    Should Be True  abs(${create}[height] - ${log_in}[height]) < 1
    Click  a >> text=go to log in
    Get Url  ==  ${LOGIN_URL}

Log in and register buttons are equally wide
    Go To  ${LOGIN_URL}
    ${log_in}=  Get BoundingBox  input[value="log in"]
    ${register}=  Get BoundingBox  a >> text=register
    Should Be True  abs(${log_in}[width] - ${register}[width]) < 1
    Should Be True  abs(${log_in}[x] - ${register}[x]) < 1

User can log in and log out
    Create User  maija
    Submit Login  maija  ${PASSWORD}
    User Should Be Logged In
    Click  .nav-right >> text=log out
    Get Url  ==  ${HOME_URL}/
    User Should Not Be Logged In
    Get Element Count  .nav-right >> text=log in  ==  1
