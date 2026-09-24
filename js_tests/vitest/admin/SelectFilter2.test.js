/* global SelectFilter */
import { afterEach, beforeEach, describe, expect, test } from "vitest";
import { page, userEvent } from "vitest/browser";
import selectBox from "../../../django/contrib/admin/static/admin/js/SelectBox.js?raw";
import selectFilter2 from "../../../django/contrib/admin/static/admin/js/SelectFilter2.js?raw";
import "../admin-globals.js";
import { loadClassicScript } from "../helpers.js";

loadClassicScript(selectBox);
loadClassicScript(selectFilter2);

const COLORS = ["Red", "Blue", "Green"];

describe("admin.SelectFilter2", () => {
    let fixture;

    beforeEach(() => {
        fixture = document.createElement("div");
        document.body.appendChild(fixture);
    });

    afterEach(() => {
        fixture.remove();
    });

    function render(html) {
        fixture.innerHTML = html;
    }

    function renderColors({ selected = [] } = {}) {
        const options = COLORS.map(
            (name, i) =>
                `<option value="${i + 1}" title="${name}"` +
                `${selected.includes(name) ? " selected" : ""}>${name}</option>`,
        ).join("");
        render(`<form><select multiple id="select">${options}</select></form>`);
        SelectFilter.init("select", "items", 0);
    }

    const available = () =>
        page.getByRole("listbox", { name: "Available items" });
    const chosen = () => page.getByRole("listbox", { name: "Chosen items" });
    const availableFilter = () =>
        page.getByRole("textbox", {
            name: "Type into this box to filter down the list of available items.",
        });
    const chosenFilter = () =>
        page.getByRole("textbox", {
            name: "Type into this box to filter down the list of selected items.",
        });
    const button = (name) => page.getByRole("button", { name });

    function optionNames(listbox) {
        return listbox
            .getByRole("option")
            .elements()
            .map((option) => option.textContent);
    }

    test("renders an accessible dual listbox", async () => {
        render(`
            <form>
                <label for="id">Test</label>
                <div class="helptext" id="id_helptext">This is helpful.</div>
                <select multiple id="id"><option value="0">A</option></select>
            </form>
        `);
        SelectFilter.init("id", "things", 0);

        const availableThings = page.getByRole("listbox", {
            name: "Available things",
        });
        const chosenThings = page.getByRole("listbox", {
            name: "Chosen things",
        });
        await expect.element(availableThings).toBeInTheDocument();
        await expect
            .element(availableThings)
            .toHaveAccessibleDescription(
                'This is helpful. Choose things by selecting them and then select the "Choose" arrow button.',
            );
        await expect.element(chosenThings).toHaveAttribute("multiple");
        await expect
            .element(chosenThings)
            .toHaveAccessibleDescription(
                'This is helpful. Remove things by selecting them and then select the "Remove" arrow button.',
            );
        expect(optionNames(availableThings)).toEqual(["A"]);
        expect(optionNames(chosenThings)).toEqual([]);

        for (const name of [
            "Choose all things",
            "Choose selected things",
            "Remove selected things",
            "Remove all things",
        ]) {
            await expect
                .element(button(name))
                .toHaveAttribute("type", "button");
        }

        await expect.element(button("Choose all things")).toBeEnabled();
        await expect.element(button("Choose selected things")).toBeDisabled();
        await expect.element(button("Remove selected things")).toBeDisabled();
        await expect.element(button("Remove all things")).toBeDisabled();

        await expect
            .element(
                page.getByRole("textbox", {
                    name: "Type into this box to filter down the list of available things.",
                }),
            )
            .toHaveAttribute("placeholder", "Filter");
        await expect
            .element(
                page.getByRole("textbox", {
                    name: "Type into this box to filter down the list of selected things.",
                }),
            )
            .toHaveAttribute("placeholder", "Filter");
    });

    test("typing in the available filter narrows the available options", async () => {
        renderColors();
        expect(optionNames(available())).toEqual(COLORS);
        expect(optionNames(chosen())).toEqual([]);

        await userEvent.type(availableFilter(), "r");

        await expect
            .element(available().getByRole("option", { name: "Blue" }))
            .not.toBeInTheDocument();
        expect(optionNames(available())).toEqual(["Red", "Green"]);
        expect(optionNames(chosen())).toEqual([]);
    });

    test("typing in the chosen filter narrows the chosen options and reports hidden ones", async () => {
        renderColors({ selected: COLORS });
        expect(optionNames(available())).toEqual([]);
        expect(optionNames(chosen())).toEqual(COLORS);

        await userEvent.type(chosenFilter(), "r");

        expect(optionNames(chosen())).toEqual(["Red", "Green"]);
        expect(optionNames(available())).toEqual([]);
        await expect
            .element(page.getByText("1 selected option not visible"))
            .toBeInTheDocument();
    });

    test("filtering the available options to nothing disables Choose all", async () => {
        renderColors();

        await userEvent.type(availableFilter(), "x");

        expect(optionNames(available())).toEqual([]);
        expect(optionNames(chosen())).toEqual([]);
        await expect.element(button("Choose all items")).toBeDisabled();
    });

    test("filtering the chosen options to nothing disables Remove all", async () => {
        renderColors({ selected: COLORS });

        await userEvent.type(chosenFilter(), "x");

        expect(optionNames(chosen())).toEqual([]);
        expect(optionNames(available())).toEqual([]);
        await expect.element(button("Remove all items")).toBeDisabled();
        await expect
            .element(page.getByText("3 selected options not visible"))
            .toBeInTheDocument();
    });

    test("highlighting an option and pressing Choose moves it to chosen", async () => {
        renderColors();
        await expect.element(button("Choose selected items")).toBeDisabled();

        await userEvent.selectOptions(available(), "Red");
        await expect.element(button("Choose selected items")).toBeEnabled();
        await button("Choose selected items").click();

        expect(optionNames(available())).toEqual(["Blue", "Green"]);
        expect(optionNames(chosen())).toEqual(["Red"]);
        await expect.element(button("Remove all items")).toBeEnabled();
    });

    test("highlighting a chosen option and pressing Remove moves it back", async () => {
        renderColors({ selected: ["Red"] });
        expect(optionNames(available())).toEqual(["Blue", "Green"]);
        expect(optionNames(chosen())).toEqual(["Red"]);

        await userEvent.selectOptions(chosen(), "Red");
        await button("Remove selected items").click();

        expect(optionNames(available())).toEqual(["Blue", "Green", "Red"]);
        expect(optionNames(chosen())).toEqual([]);
    });

    test("arrow keys in the available filter highlight and choose an option", async () => {
        renderColors();

        await userEvent.type(availableFilter(), "r");
        await userEvent.keyboard("{ArrowDown}{ArrowRight}");

        expect(optionNames(chosen())).toEqual(["Red"]);
        expect(optionNames(available())).toEqual(["Green"]);
    });

    test("arrow keys in the chosen filter highlight and remove an option", async () => {
        renderColors({ selected: ["Red"] });

        await userEvent.type(chosenFilter(), "r");
        await userEvent.keyboard("{ArrowDown}{ArrowLeft}");

        expect(optionNames(chosen())).toEqual([]);
        expect(optionNames(available())).toEqual(["Blue", "Green", "Red"]);
    });
});
