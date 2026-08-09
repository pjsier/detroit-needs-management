import {
  createEffect,
  createMemo,
  createSignal,
  onMount,
  onCleanup,
  For,
  Show,
} from "solid-js"
import { createStore } from "solid-js/store"
import { createIntersectionObserver } from "@solid-primitives/intersection-observer"
import { updateQueryParams, haversine } from "../utils"
import Geocoder from "./geocoder"
import Result from "./result"
import UpArrowIcon from "./icons/up-arrow-icon"

const PAGE_SIZE = 25

const SEARCH_DISTANCES = [5, 15, 25, 50, 100]

const DEBOUNCE_TIME = 350

/* eslint-disable */
// Debounce function from underscore
export const debounce = (func, wait, immediate) => {
  let timeout
  return function () {
    const context = this
    const args = arguments
    const later = () => {
      timeout = null
      if (!immediate) func.apply(context, args)
    }
    const callNow = immediate && !timeout
    clearTimeout(timeout)
    timeout = setTimeout(later, wait)
    if (callNow) func.apply(context, args)
  }
}
/* eslint-enable */

function stateFromParams(params) {
  return {
    address: params.get("address"),
    coordinates: (params.get("coordinates") || "")
      .split(",")
      .filter((v) => !!v)
      .map((v) => +v),
    withinRange: +(params.get("withinRange") || 15),
    // TODO:
    // services:
    //   (params.get("services") || "").split(",").filter((svc) => !!svc) || [],
    page: +params.get("page") || 1,
  }
}

function filterResults(data, coordinates, services, withinRange) {
  return data
    .map((result) =>
      coordinates && result.coordinates
        ? { ...result, distance: haversine(coordinates, result.coordinates) }
        : { ...result, distance: null }
    )
    .filter((result) => {
      if (
        services?.length > 0 &&
        !services.some((service) => result.services.includes(service))
      ) {
        return false
      } else if (
        coordinates &&
        haversine(coordinates, result.coordinates) > withinRange
      ) {
        return false
      }
      return true
    })
    .sort((a, b) => {
      const av = a.distance
      const bv = b.distance
      if (av == null && bv == null) return 0
      if (av == null) return 1
      if (bv == null) return -1

      return av < bv ? -1 : av > bv ? 1 : 0
    })
}

function filtersHaveValues(filters) {
  return !!Object.entries(filters).find(([key, value]) =>
    key === `page` ? value > 1 : !!value
  )
}

const FilterComponent = (props) => {
  const [state, setState] = createStore({
    address: ``,
    coordinates: null,
    services: [],
    withinRange: 15,
    page: 1,
    showScrollTop: false,
    usingLocation: false,
    locationEnabled: true,
    isLocating: false,
    isPrinting: false,
  })

  const services = createMemo(() => [
    ...new Set(props.data.map(({ services }) => services).flat()),
  ])

  const results = createMemo(() =>
    filterResults(
      props.data,
      state.coordinates,
      state.services,
      state.withinRange
    )
  )

  const useMyLocation = (e) => {
    if (!navigator.geolocation) {
      alert("Location is not supported in your browser")
      setState({ locationEnabled: false })
      return
    }
    if (!e.target.checked) {
      setState({ usingLocation: false, coordinates: null })
      return
    }

    setState({ usingLocation: true, isLocating: true })
    navigator.geolocation.getCurrentPosition(
      (position) =>
        setFilters({
          coordinates: [position.coords.longitude, position.coords.latitude],
          isLocating: false,
        }),
      (_) => {
        setState({
          usingLocation: false,
          isLocating: false,
          locationEnabled: false,
        })
        alert("Unable to get your location")
      }
    )
  }

  onMount(() => {
    const params = new URLSearchParams(window.location.search)
    setState(stateFromParams(params))

    const media = window.matchMedia("print")

    const mediaChangeHandler = (e) => {
      setState({ isPrinting: e.matches })
    }

    media.addEventListener("change", mediaChangeHandler)

    onCleanup(() => media.removeEventListener("change", mediaChangeHandler))
  })

  const [filterForm, setFilterForm] = createSignal()
  const [resultsEnd, setResultsEnd] = createSignal()

  createIntersectionObserver(
    () => [filterForm(), resultsEnd()],
    (entries) => {
      for (const entry of entries) {
        if (
          entry.target === resultsEnd() &&
          entry.isIntersecting &&
          state.page < Math.ceil(results().length / PAGE_SIZE)
        ) {
          setState("page", (page) => page + 1)
        }

        if (entry.target === filterForm()) {
          setState("showScrollTop", !entry.isIntersecting)
        }
      }
    },
    {
      rootMargin: "0px 0px 500px 0px",
    }
  )

  createEffect(() => {
    updateQueryParams({
      address: state.address,
      coordinates: state.coordinates,
      search: state.search,
      services: state.services,
      withinRange: state.withinRange,
      page: state.page,
    })
  })

  const setFilters = (filters) => setState({ ...filters, page: 1 })

  const useLocationMessage = ({
    usingLocation,
    locationEnabled,
    isLocating,
  }) => {
    if (isLocating) {
      return "Getting your location..."
    } else if (!locationEnabled) {
      return "Unable to get your location"
    } else if (usingLocation) {
      return "Using your location"
    } else {
      return "Use my location"
    }
  }

  const debouncedSetFilters = debounce(setFilters, DEBOUNCE_TIME)

  const displayedResults = createMemo(() =>
    results().slice(
      0,
      state.isPrinting ? results().length : PAGE_SIZE * state.page
    )
  )

  return (
    <>
      <Show when={state.showScrollTop}>
        <button
          aria-label="Scroll to top"
          id="scroll-to-top"
          onClick={() => window.scroll({ top: 0, left: 0, behavior: "smooth" })}
        >
          <UpArrowIcon />
        </button>
      </Show>
      <form class="filter-form" action="" method="GET" ref={setFilterForm}>
        <div id="geocoder-container">
          <Geocoder
            onSelect={({ address, lat, lon }) =>
              setFilters({
                address,
                coordinates: [lat, lon],
                usingLocation: false,
              })
            }
          />
        </div>
        <div>
          <label for="use_my_location">
            <span>{useLocationMessage(state)}</span>
            <input
              type="checkbox"
              name="use_my_location"
              id="use_my_location"
              disabled={!state.locationEnabled || state.isLocating}
              checked={state.usingLocation}
              onChange={useMyLocation}
            />
          </label>
        </div>
        <div class="select-row">
          <label for="within_range">Within</label>
          <div class="select">
            <select
              id="within_range"
              name="within_range"
              value={state.withinRange}
              onChange={(e) => setFilters({ withinRange: e.target.value })}
            >
              <For each={SEARCH_DISTANCES}>
                {(distance) => (
                  <option id={`within_range_${distance}`} value={distance}>
                    {distance} miles
                  </option>
                )}
              </For>
            </select>
          </div>
        </div>
        <fieldset>
          <legend>Services</legend>
          {services().map((service, idx) => (
            <label for={`service_${idx}`}>
              <input
                type="checkbox"
                id={`service_${idx}`}
                name={`service_${idx}`}
                checked={state.services.includes(service)}
                onChange={(e) => {
                  setState({
                    services: [
                      ...state.services.filter((svc) => svc !== service),
                      ...(e.target.checked ? [service] : []),
                    ],
                  })
                }}
              />
              <span>{service}</span>
            </label>
          ))}
        </fieldset>
        <div class="results-row">
          <p aria-live="polite" aria-atomic="true" class="result-count">
            {`${results().length.toLocaleString()} ${
              results().length === 1 ? `result` : `results`
            }`}
          </p>
          {filtersHaveValues(state) && (
            <button
              type="button"
              onClick={() =>
                setState({
                  address: ``,
                  coordinates: null,
                  services: [],
                  page: 1,
                })
              }
            >
              Clear filters
            </button>
          )}
        </div>
      </form>
      <div class="filter-results">
        <For each={displayedResults()}>
          {({ coordinates, ...result }) => (
            <Result
              distance={
                state.coordinates
                  ? haversine(state.coordinates, coordinates)
                  : null
              }
              {...result}
            />
          )}
        </For>
      </div>
      <div ref={setResultsEnd} id="results-end" aria-hidden="true"></div>
    </>
  )
}

export default FilterComponent
