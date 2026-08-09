import LinkIcon from "./icons/link-icon"
import PhoneIcon from "./icons/phone-icon"
import { Show } from "solid-js"

// Tag chips for individual flags

const cleanPhone = (phone) => {
  let numericPhone = phone.replace(/\D/g, "")
  return numericPhone.startsWith("1") ? `+${numericPhone}` : `+1${numericPhone}`
}

const cleanContent = (description, notes, additional_info) => [
  ...(description || "").split("\n"),
  ...(notes || "").split("\n"),
  ...(additional_info || "").split("\n"),
]

const Rental = (props) => {
  return (
    <div class="filter-result">
      <p>
        {props.address} {props.city} {props.zipcode}, {props.area}
      </p>
      <p>
        <Show when={props.link} fallback={props.rental_category}>
          <a href={props.link}>
            <LinkIcon />
            &nbsp;{props.rental_category}
          </a>
        </Show>
      </p>
      <Show when={props.phone}>
        <p>
          <a href={`tel:${cleanPhone(props.phone)}`}>
            <PhoneIcon /> {props.phone}
          </a>
        </p>
      </Show>
      <p>
        <strong>Owner:</strong> {props.owner}
      </p>
      <div class="detail-row">
        <div>
          <strong>Rent:</strong> ${props.rent}
        </div>
        <div>
          <strong>Gross rent:</strong> ${props.gross_rent}
        </div>
        <div>
          <strong>Deposit:</strong> ${props.deposit}
        </div>
      </div>
      <div class="detail-row">
        <div>
          <strong>Beds:</strong> {props.bed}
        </div>
        <div>
          <strong>Baths:</strong> {props.bath}
        </div>
        <div>
          <strong>Utility Allowance:</strong> ${props.utility_allowance}
        </div>
      </div>
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

export default Rental
