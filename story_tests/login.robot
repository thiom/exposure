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

Login fails with a wrong password
    Create User  maija
    Submit Login  maija  wrong-password
    Get Text  .flash  *=  Wrong username or password
    User Should Not Be Logged In

User can log in and log out
    Create User  maija
    Submit Login  maija  ${PASSWORD}
    User Should Be Logged In
    Click  .nav-right >> text=log out
    Get Url  ==  ${HOME_URL}/
    User Should Not Be Logged In
    Get Element Count  .nav-right >> text=log in  ==  1
