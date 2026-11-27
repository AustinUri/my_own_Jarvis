import raw from './business.json'

type Business = {
  language: string
  name: string
  category: string
  city?: string
  address?: string
  phone?: string
  whatsapp?: string
  tagline?: string
  services: string[]
}

const business: Business = raw
const he = business.language === 'he'
const automotive = /מוסך|תיקוני רכב|automotive|auto repair|garage|motor repair/i.test(business.category)
const garden = /פרחים|משתלה|גינון|florist|nursery|garden/i.test(business.category)
const words = he ? {
  skip: 'דילוג לתוכן', navigation: 'ניווט ראשי', services: 'שירותים', contact: 'יצירת קשר',
  call: automotive ? 'התקשרו למוסך' : 'התקשרו אלינו', whatsapp: 'הודעה בוואטסאפ',
  phone: 'טלפון', place: 'מיקום', address: 'כתובת', discover: 'לכל השירותים',
  art: 'איור טכני', disc: 'דיסק בלם', pending: 'פרטי ההתקשרות ממתינים לאישור העסק.',
  contactHeading: automotive ? 'דברו עם המוסך' : 'דברו איתנו',
  servicesHeading: automotive ? 'שירותי המוסך' : 'השירותים שלנו',
  top: 'לראש העמוד', demo: 'הדגמת עיצוב פרטית · ממתינה לאישור העסק',
} : {
  skip: 'Skip to content', navigation: 'Main navigation', services: 'Services', contact: 'Contact',
  call: automotive ? 'Call the workshop' : 'Call us', whatsapp: 'Message on WhatsApp',
  phone: 'Telephone', place: 'Location', address: 'Address', discover: 'Explore services',
  art: 'Technical illustration', disc: 'Brake disc', pending: 'Contact details are awaiting business approval.',
  contactHeading: automotive ? 'Talk to the workshop' : 'Get in touch',
  servicesHeading: automotive ? 'Workshop services' : 'Our services',
  top: 'Back to top', demo: 'Private design preview · Awaiting business approval',
}

type IconName = 'phone' | 'arrow' | 'down' | 'pin' | 'wrench' | 'engine' | 'gear' | 'wheel' | 'bubble'
const paths: Record<IconName, string> = {
  phone: 'M7.4 3.1 10 7.3 7.9 9.8a14.4 14.4 0 0 0 6.3 6.3l2.5-2.1 4.2 2.6c.3.2.5.6.4 1-.5 2.4-1.7 3.5-3.5 3.5C10 21.1 2.9 14 2.9 6.2c0-1.8 1.1-3 3.5-3.5.4-.1.8.1 1 .4Z',
  arrow: 'M4 12h16m-6-6 6 6-6 6',
  down: 'M12 4v16m-6-6 6 6 6-6',
  pin: 'M19.5 10c0 5.4-7.5 11-7.5 11s-7.5-5.6-7.5-11a7.5 7.5 0 1 1 15 0Zm-5.1 0a2.4 2.4 0 1 1-4.8 0 2.4 2.4 0 0 1 4.8 0Z',
  wrench: 'M20.2 3.5a5.6 5.6 0 0 0-7.3 7.3L4 18.9a1.7 1.7 0 0 0 2.5 2.4l8.4-8.8a5.6 5.6 0 0 0 6.8-7l-3.9 3.9-3-3 3.8-3.6',
  engine: 'M3 10h3l3-3h6l3 3h3v8h-4l-2 2H8l-3-4H3Zm6-6h7m-3.5 0v3M1 9v8',
  gear: 'm9 3 1.2-1h3.6L15 5l2.5 1 2.7-.2 1.6 3-1.8 2v2.5l1.6 2-1.8 3.1-2.7-.4-2.3 1.3-1 2.7h-3.6l-1.1-2.8-2.4-1.2-2.7.3L2.4 15l1.7-2.2v-2.5L2.4 8.4l1.8-3.1 2.7.4L9 4.5Zm6.5 9a3.5 3.5 0 1 1-7 0 3.5 3.5 0 0 1 7 0Z',
  wheel: 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-6 0a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm-3-3V5m2 5 3.7-2m-3.1 5.7 3.5 2M10.4 14.5l-2.1 3.6M9 12H5',
  bubble: 'M21 11.5a8.7 8.7 0 0 1-8.8 8.5c-1.7 0-3.2-.3-4.5-1L3 20.2l1.3-4.6A8.2 8.2 0 0 1 3 11.5a9 9 0 0 1 18 0Z',
}

function Icon({ name }: { name: IconName }) {
  return <svg aria-hidden="true" className={'icon icon-' + name} viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round"><path d={paths[name]}/></svg>
}

function BrandMark() {
  return <svg aria-hidden="true" className="brand-mark" viewBox="0 0 44 38" fill="currentColor">
    <path d="M1 31 17 7h8L9 31zm12 0L29 7h8L21 31zm12 0 10-15 4 6-6 9z"/>
  </svg>
}

function ContactLink({ header = false }: { header?: boolean }) {
  const phone = business.phone
  const wa = business.whatsapp
  const href = phone ? 'tel:' + phone : wa ? 'https://wa.me/' + wa.replace(/^\+/, '') : '#contact'
  const label = phone ? words.call : wa ? words.whatsapp : words.contact
  return <a className={header ? 'header-action' : 'button primary'} href={href}>
    <Icon name={phone ? 'phone' : wa ? 'bubble' : 'arrow'}/>{label}</a>
}

function localizedPhone(number: string) {
  if (he && /^\+972[2-489]\d{7}$/.test(number)) return '0' + number.slice(4, 5) + '-' + number.slice(5)
  if (he && /^\+972[57]\d{8}$/.test(number)) return '0' + number.slice(4, 6) + '-' + number.slice(6)
  return number
}

function serviceIcon(service: string): IconName {
  if (/מנוע|engine/i.test(service)) return 'engine'
  if (/גיר|הילוכ|gear|transmission/i.test(service)) return 'gear'
  if (/בלמ|גלגל|צמיג|brake|wheel|tyre|tire/i.test(service)) return 'wheel'
  return 'wrench'
}

function Services() {
  if (!business.services.length) return null
  return <section id="services" className="services content-band" aria-labelledby="service-title">
    <h2 id="service-title">{words.servicesHeading}</h2>
    <ul className="service-list">{business.services.map(service =>
      <li key={service}>{automotive && <span className="service-icon"><Icon name={serviceIcon(service)}/></span>}
        <span dir="auto">{service}</span></li>)}</ul>
  </section>
}

function Contact() {
  return <section className="contact" id="contact" aria-labelledby="contact-title">
    <div className="content-band contact-band">
      <h2 id="contact-title">{words.contactHeading}</h2>
      <div className="contact-details">
        {business.phone && <a href={'tel:' + business.phone} className="contact-number">
          <Icon name="phone"/><bdi dir="ltr">{localizedPhone(business.phone)}</bdi></a>}
        {(business.address || business.city) && <p className="contact-place"><Icon name="pin"/>
          <span><span className="detail-label">{business.address ? words.address : words.place}</span>
          {[business.address, business.city].filter(Boolean).join(', ')}</span></p>}
        {business.whatsapp && <a className="whatsapp" href={'https://wa.me/' + business.whatsapp.replace(/^\+/, '')}>
          <Icon name="bubble"/>{words.whatsapp}</a>}
        {!business.phone && !business.whatsapp && <p>{words.pending}</p>}
      </div>
    </div>
  </section>
}

export default function App() {
  const hasServices = business.services.length > 0
  const firstSpace = business.name.indexOf(' ')
  const wrapName = automotive && firstSpace > 0 && firstSpace < 10
  return <div className={'site ' + (automotive ? 'automotive' : garden ? 'garden' : 'studio')} id="top">
    <a className="skip" href="#main">{words.skip}</a>
    <header className="masthead">
      <div className="masthead-inner">
        <a className="brand" href="#top"><BrandMark/><bdi>{business.name}</bdi></a>
        <nav aria-label={words.navigation}>{hasServices && <a href="#services">{words.services}</a>}<a href="#contact">{words.contact}</a></nav>
        <ContactLink header/>
      </div>
    </header>
    <main id="main" tabIndex={-1}>
      <section className="hero" aria-labelledby="title">
        <div className="hero-copy">
          <div className="hero-heading">
            <h1 id="title">{wrapName ? <><span>{business.name.slice(0, firstSpace)}</span>{' '}
              <span>{business.name.slice(firstSpace + 1)}</span></> : business.name}</h1>
            <p className="identity">{business.category}{business.city && <><i aria-hidden="true"/>{business.city}</>}</p>
          </div>
          {business.tagline && <p className="tagline">{business.tagline}</p>}
          <div className="hero-actions"><ContactLink/>{hasServices &&
            <a className="text-action" href="#services">{words.discover}<Icon name="down"/></a>}</div>
        </div>
        {automotive && <figure className="study">
          <img src="./assets/brake-rotor.webp" width="1200" height="1000" alt="" fetchPriority="high"/>
          <figcaption><span>{words.disc}</span><span>{words.art}</span></figcaption>
        </figure>}
      </section>
      <Services/><Contact/>
    </main>
    <footer><div className="footer-inner"><span className="footer-brand">{business.name}</span>
      <small>{words.demo}</small><a href="#top">{words.top}<Icon name="down"/></a></div></footer>
  </div>
}
