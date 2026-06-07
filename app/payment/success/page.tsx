export default function PaymentSuccessPage({ searchParams }: { searchParams: { session_id?: string } }) {
  return (
    <main className="shell">
      <section className="panel">
        <p className="eyebrow">Already Here LLC</p>
        <h1>Payment Submitted</h1>
        <p className="subhead">Stripe received the payment submission. Already Here LLC will confirm the final paid status after secure verification.</p>
        {searchParams.session_id && <p className="detail"><strong>Session reference</strong><span>{searchParams.session_id}</span></p>}
      </section>
    </main>
  );
}
