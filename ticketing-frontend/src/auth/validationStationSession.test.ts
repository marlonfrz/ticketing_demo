import { describe, expect, it } from "vitest";

import {
  getValidationStationCookieHeader,
  VALIDATION_STATION_COOKIE,
} from "./validationStationSession";

describe("validation station server credentials", () => {
  it("forwards the station session only to validation station routes", () => {
    expect(
      getValidationStationCookieHeader(
        ["validator-stations", "me"],
        "header.payload_signature"
      )
    ).toBe(`${VALIDATION_STATION_COOKIE}=header.payload_signature`);

    expect(
      getValidationStationCookieHeader(["auth", "me"], "header.payload_signature")
    ).toBeNull();
  });

  it("does not build a cookie header from missing or unsafe values", () => {
    expect(
      getValidationStationCookieHeader(["validator-stations", "me"], undefined)
    ).toBeNull();
    expect(
      getValidationStationCookieHeader(
        ["validator-stations", "me"],
        "token; injected=value"
      )
    ).toBeNull();
  });
});
