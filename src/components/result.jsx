import LinkIcon from "./icons/link-icon"
import PhoneIcon from "./icons/phone-icon"
import { Show } from "solid-js"

const Result = (props) => {
  return (
    <div class="filter-result">
      <p class="label">
        {props.website ? (
          <a target="_blank" rel="noopener noreferrer" href={props.website}>
            {props.name}&nbsp;
            <LinkIcon />
          </a>
        ) : (
          props.name
        )}
      </p>
      <p>{props.services}</p>
      <p>
        {props.address}
      </p>
      <p>
        <a href={`tel:${props.phone}`}>
          <PhoneIcon /> {props.phone}
        </a>
      </p>
      <Show when={props.distance > 0}>
        <p>
          <span>Distance: </span>
          <span>
            {new Intl.NumberFormat("en-US", {
              style: "unit",
              unit: "mile",
              unitDisplay: "long",
              maximumFractionDigits: 1,
            }).format(props.distance)}
          </span>
        </p>
      </Show>
    </div>
  )
}

export default Result
