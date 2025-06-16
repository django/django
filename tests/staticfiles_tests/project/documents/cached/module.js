export const moduleConst = "module";
// Static imports.
import rootConst from "/static/absolute_root.js";
import testConst from "./module_test.js";
import * as NewModule from "./module_test.js";
import*as m from "./module_test.js";
import *as m from "./module_test.js";
import* as m from "./module_test.js";
import*  as  m from "./module_test.js";
import { testConst as alias } from "./module_test.js";
import { firstConst, secondConst } from "./module_test.js";
import {
    firstVar1 as firstVarAlias,
    $second_var_2 as secondVarAlias
} from "./module_test.js";
import relativeModule from "../nested/js/nested.js";

// Dynamic imports.
const dynamicModule = import("./module_test.js");

// import with assert
import k from"./other.css"assert{type:"css"};

import*as l from "/static/absolute_root.js";
import*as h from "/static/absolute_root.js";
import*as m from "/static/absolute_root.js";
import {BaseComponent as g} from "/static/absolute_root.js";


// Modules exports to aggregate modules.
export * from "./module_test.js";
export { testConst } from "./module_test.js";
export {
    firstVar as firstVarAlias,
    secondVar as secondVarAlias
} from "./module_test.js";


// These should not be processed
// @returns {import("./non-existent-1").something}
/* @returns {import("./non-existent-2").something} */
'import("./non-existent-3")'
"import('./non-existent-4')"
`import("./non-existent-5")`
r = /import/;
/**
 * @param {HTMLElement} elt
 * @returns {import("./htmx").HtmxTriggerSpecification[]}
 */

//Technically valid but not supported as it should be a real edge case
`${import("./module_test.js")}`