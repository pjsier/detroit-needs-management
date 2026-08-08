import LinkIcon from "./icons/link-icon"
import PhoneIcon from "./icons/phone-icon"
import { Show } from "solid-js"

// Tag chips for individual flags

const cleanPhone = (phone) => {
  let numericPhone = phone.replace(/\D/g, '')
  return numericPhone.startsWith("1") ? `+${numericPhone}` : `+1${numericPhone}`
}


const cleanContent = (description, notes, additional_info) => [...(description || "").split("\n"), ...(notes || "").split("\n"), ...(additional_info || "").split("\n")]

const Result = (props) => {
  const content = cleanContent(props.description, props.notes, props.additional_info)
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
      <p>{props.services.join(", ")}</p>
      <p>
        {props.address}
      </p>
      <Show when={props.phone}>
        <p>
          <a href={`tel:${cleanPhone(props.phone)}`}>
            <PhoneIcon /> {props.phone}
          </a>
        </p>
      </Show>
      <Show when={content.length > 0}>
        <div class="content-row">
          <For each={content}>
            {(contentLine) => <p>{contentLine}</p>}
          </For>
        </div>
      </Show>
      <Show when={props.disclaimer}>
        <p>
          <em>{props.disclaimer}</em>
        </p>
      </Show>
      {/* TODO: Combine description, other info in content-ish field */}
      <Show when={props.distance > 0}>
        <p>
          <strong>Distance: </strong>
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
