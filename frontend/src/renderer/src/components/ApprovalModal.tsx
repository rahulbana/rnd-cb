import type { ApprovalRequest } from '../../../shared/types'

interface Props {
  request: ApprovalRequest
  onRespond: (approved: boolean) => void
}

export default function ApprovalModal({ request, onRespond }: Props): JSX.Element {
  return (
    <div className="modal-overlay">
      <div className="modal">
        <h3>Approve action?</h3>
        <p className="modal-summary">{request.summary}</p>
        {request.details && <pre className="modal-details">{request.details}</pre>}
        <div className="modal-actions">
          <button className="btn-secondary" onClick={() => onRespond(false)}>
            Decline
          </button>
          <button className="btn-primary" onClick={() => onRespond(true)}>
            Approve
          </button>
        </div>
      </div>
    </div>
  )
}
