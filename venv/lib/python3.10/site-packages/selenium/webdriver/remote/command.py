# Licensed to the Software Freedom Conservancy (SFC) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The SFC licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.


class Command:
    """Defines constants for the standard WebDriver commands.

    While these constants have no meaning in and of themselves, they are
    used to marshal commands through a service that implements WebDriver's
    remote wire protocol:

        https://w3c.github.io/webdriver/
    """

    # Keep in sync with org.openqa.selenium.remote.DriverCommand

    NEW_SESSION: str = "newSession"
    DELETE_SESSION: str = "deleteSession"
    NEW_WINDOW: str = "newWindow"
    CLOSE: str = "close"
    QUIT: str = "quit"
    GET: str = "get"
    GO_BACK: str = "goBack"
    GO_FORWARD: str = "goForward"
    REFRESH: str = "refresh"
    ADD_COOKIE: str = "addCookie"
    GET_COOKIE: str = "getCookie"
    GET_ALL_COOKIES: str = "getCookies"
    DELETE_COOKIE: str = "deleteCookie"
    DELETE_ALL_COOKIES: str = "deleteAllCookies"
    FIND_ELEMENT: str = "findElement"
    FIND_ELEMENTS: str = "findElements"
    FIND_CHILD_ELEMENT: str = "findChildElement"
    FIND_CHILD_ELEMENTS: str = "findChildElements"
    CLEAR_ELEMENT: str = "clearElement"
    CLICK_ELEMENT: str = "clickElement"
    SEND_KEYS_TO_ELEMENT: str = "sendKeysToElement"
    UPLOAD_FILE: str = "uploadFile"
    W3C_GET_CURRENT_WINDOW_HANDLE: str = "w3cGetCurrentWindowHandle"
    W3C_GET_WINDOW_HANDLES: str = "w3cGetWindowHandles"
    SET_WINDOW_RECT: str = "setWindowRect"
    GET_WINDOW_RECT: str = "getWindowRect"
    SWITCH_TO_WINDOW: str = "switchToWindow"
    SWITCH_TO_FRAME: str = "switchToFrame"
    SWITCH_TO_PARENT_FRAME: str = "switchToParentFrame"
    W3C_GET_ACTIVE_ELEMENT: str = "w3cGetActiveElement"
    GET_CURRENT_URL: str = "getCurrentUrl"
    GET_PAGE_SOURCE: str = "getPageSource"
    GET_TITLE: str = "getTitle"
    W3C_EXECUTE_SCRIPT: str = "w3cExecuteScript"
    W3C_EXECUTE_SCRIPT_ASYNC: str = "w3cExecuteScriptAsync"
    GET_ELEMENT_TEXT: str = "getElementText"
    GET_ELEMENT_TAG_NAME: str = "getElementTagName"
    IS_ELEMENT_SELECTED: str = "isElementSelected"
    IS_ELEMENT_ENABLED: str = "isElementEnabled"
    GET_ELEMENT_RECT: str = "getElementRect"
    GET_ELEMENT_ATTRIBUTE: str = "getElementAttribute"
    GET_ELEMENT_PROPERTY: str = "getElementProperty"
    GET_ELEMENT_VALUE_OF_CSS_PROPERTY: str = "getElementValueOfCssProperty"
    GET_ELEMENT_ARIA_ROLE: str = "getElementAriaRole"
    GET_ELEMENT_ARIA_LABEL: str = "getElementAriaLabel"
    SCREENSHOT: str = "screenshot"
    ELEMENT_SCREENSHOT: str = "elementScreenshot"
    EXECUTE_ASYNC_SCRIPT: str = "executeAsyncScript"
    SET_TIMEOUTS: str = "setTimeouts"
    GET_TIMEOUTS: str = "getTimeouts"
    W3C_MAXIMIZE_WINDOW: str = "w3cMaximizeWindow"
    GET_LOG: str = "getLog"
    GET_AVAILABLE_LOG_TYPES: str = "getAvailableLogTypes"
    FULLSCREEN_WINDOW: str = "fullscreenWindow"
    MINIMIZE_WINDOW: str = "minimizeWindow"
    PRINT_PAGE: str = "printPage"

    # Alerts
    W3C_DISMISS_ALERT: str = "w3cDismissAlert"
    W3C_ACCEPT_ALERT: str = "w3cAcceptAlert"
    W3C_SET_ALERT_VALUE: str = "w3cSetAlertValue"
    W3C_GET_ALERT_TEXT: str = "w3cGetAlertText"

    # Advanced user interactions
    W3C_ACTIONS: str = "actions"
    W3C_CLEAR_ACTIONS: str = "clearActionState"

    # Screen Orientation
    SET_SCREEN_ORIENTATION: str = "setScreenOrientation"
    GET_SCREEN_ORIENTATION: str = "getScreenOrientation"

    # Mobile
    GET_NETWORK_CONNECTION: str = "getNetworkConnection"
    SET_NETWORK_CONNECTION: str = "setNetworkConnection"
    CURRENT_CONTEXT_HANDLE: str = "getCurrentContextHandle"
    CONTEXT_HANDLES: str = "getContextHandles"
    SWITCH_TO_CONTEXT: str = "switchToContext"

    # Web Components
    GET_SHADOW_ROOT: str = "getShadowRoot"
    FIND_ELEMENT_FROM_SHADOW_ROOT: str = "findElementFromShadowRoot"
    FIND_ELEMENTS_FROM_SHADOW_ROOT: str = "findElementsFromShadowRoot"

    # Virtual Authenticator
    ADD_VIRTUAL_AUTHENTICATOR: str = "addVirtualAuthenticator"
    REMOVE_VIRTUAL_AUTHENTICATOR: str = "removeVirtualAuthenticator"
    ADD_CREDENTIAL: str = "addCredential"
    GET_CREDENTIALS: str = "getCredentials"
    REMOVE_CREDENTIAL: str = "removeCredential"
    REMOVE_ALL_CREDENTIALS: str = "removeAllCredentials"
    SET_USER_VERIFIED: str = "setUserVerified"
