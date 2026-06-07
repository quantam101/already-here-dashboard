export default function PaymentCancelledPage({ searchParams }: { searchParams: { ref?: string } }) {
  return (
    <main className="shell">
      <section className="panel">
        <p className="eyebrow">Already Here LLC</p>
        <h1>Payment Not Completed</h1>
        <p className="subhead">The Stripe payment page was closed before completion. Your service record is not marked paid yet.</p>
        {searchParams.ref && <p className="detail"><strong>Reference</strong><span>{searchParams.ref}</span></p>}
      </section>
    </main>
  );
}
