*** Settings ***
Resource  resource.robot
Suite Setup      Open And Configure Browser
Suite Teardown   Close Browser
Test Setup       Reset Application And Add Photos

*** Keywords ***
Reset Application And Add Photos
    Reset Application
    Submit Registration  maija  ${PASSWORD}  ${PASSWORD}
    Add Photo  First photo
    Add Photo  Second photo

Create Collection
    [Arguments]  ${title}=Night walks  ${description}=Evenings by the sea
    Go To  ${HOME_URL}/my_collections
    Click  .add-new
    Fill Text  id=title  ${title}
    Fill Text  id=description  ${description}
    Click  button.add-plus >> nth=0
    Click  button.add-plus >> nth=0
    Click  button[name="save"]
    Get Url  matches  ${HOME_URL}/collection/\\d+$

*** Test Cases ***
Collection count on my collections is mirrored with the plus button
    Create Collection
    Create Collection  Day walks
    Go To  ${HOME_URL}/my_collections
    Get Text  .item-count  ==  2 collections
    Mirrored With Plus Button  .item-count  .collection-list

Plus button on my collections is a sixth of the image height
    Create Collection
    Go To  ${HOME_URL}/my_collections
    ${plus}=  Get BoundingBox  .add-new
    ${image}=  Get BoundingBox  .collection-card img
    Should Be True  abs(${plus}[height] - ${image}[height] / 6) < 2
    Should Be True  abs(${plus}[y] - ${image}[y]) < 2

Without collections the text is centered below the plus button
    Go To  ${HOME_URL}/my_collections
    ${latest}=  Get BoundingBox  .nav-left >> text=latest
    ${plus}=  Get BoundingBox  .add-new
    ${text}=  Get BoundingBox  .empty >> text=You have not created any collections yet.
    Should Be True  abs(${plus}[x] - ${latest}[x]) < 2
    Should Be True  ${plus}[y] + ${plus}[height] <= ${text}[y]
    Get Style  .empty  text-align  ==  center

User can create a collection
    Go To  ${HOME_URL}/my_collections
    Click  .add-new
    Fill Text  id=title  Night walks
    Click  button.add-plus >> nth=0
    Get Text  id=selected  *=  in this collection (1 / 50)
    Get Element Count  button.add-plus  ==  1
    # the typed title is kept when a photo is added
    Get Property  id=title  value  ==  Night walks
    Click  button.add-plus
    Get Element Count  button.add-plus  ==  0
    Click  button[name="save"]
    Get Text  .collection-header h1  ==  Night walks
    Get Element Count  .photo-list img  ==  2

Creating a collection without photos fails
    Go To  ${HOME_URL}/my_collections
    Click  .add-new
    Fill Text  id=title  Empty
    Click  button[name="save"]
    Get Url  ==  ${HOME_URL}/collection_draft
    Get Text  .flash  *=  Add at least one photo

User can reorder and rename a collection
    Create Collection
    ${first}=  Get Attribute  .photo-list img >> nth=0  alt
    Click  .collection-header >> text=edit
    Click  button[name="up"]:not([disabled])
    Fill Text  id=title  Night walks 2
    Click  button[name="save"]
    Get Text  .collection-header h1  ==  Night walks 2
    Get Attribute  .photo-list img >> nth=1  alt  ==  ${first}

New collection is shown on latest collections and can be searched
    Create Collection
    Go To  ${HOME_URL}/latest
    Click  .tabs >> text=collections
    Get Url  ==  ${HOME_URL}/collections
    Get Text  .collection-card  *=  Night walks
    Get Text  .collection-card  *=  by maija
    Fill Text  id=query  by the sea
    Click  input[value="search"]
    Get Element Count  .collection-card  ==  1
    Fill Text  id=query  mountains
    Click  input[value="search"]
    Get Text  .empty  ==  No collections found.

User can delete a collection
    Create Collection
    Click  .collection-header >> text=edit
    Click  text=delete collection
    Click  input[name="remove"]
    Get Url  ==  ${HOME_URL}/my_collections
    Get Text  .empty  *=  You have not created any collections yet
    # the photos are not deleted with the collection
    Go To  ${HOME_URL}/my_photos
    Get Element Count  .photo-list img  ==  2
