import pytest
import pytest_asyncio
from cryptography import x509
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CertificateAuthority, CertificateType
from app.services.ca import CAService
from app.services.cert import CertificateService
from app.services.exceptions import HasDependentsError, LeafCertNotAllowedError


@pytest_asyncio.fixture
async def root_ca(db: AsyncSession) -> CertificateAuthority:
    """Create a root CA with no path_length constraint."""
    ca_service = CAService(db)
    return await ca_service.create_ca(
        name="Root CA",
        subject_dn="CN=Root CA,O=Test Organization,C=US",
        key_size=2048,
        valid_days=3650,
    )


@pytest_asyncio.fixture
async def root_ca_with_path_length(db: AsyncSession) -> CertificateAuthority:
    """Create a root CA with path_length=2."""
    ca_service = CAService(db)
    return await ca_service.create_ca(
        name="Root CA PL2",
        subject_dn="CN=Root CA PL2,O=Test Organization,C=US",
        key_size=2048,
        valid_days=3650,
        path_length=2,
    )


@pytest.mark.asyncio
async def test_root_ca_backward_compatibility(db: AsyncSession):
    """Root CA creation still works with no parent_ca_id."""
    ca_service = CAService(db)
    ca = await ca_service.create_ca(
        name="Compat Root",
        subject_dn="CN=Compat Root,O=Test,C=US",
        key_size=2048,
        valid_days=365,
    )
    assert ca.id is not None
    assert ca.parent_ca_id is None
    assert ca.path_length is None


@pytest.mark.asyncio
async def test_root_ca_with_explicit_path_length(db: AsyncSession):
    """Root CA can be created with an explicit path_length."""
    ca_service = CAService(db)
    ca = await ca_service.create_ca(
        name="Root PL",
        subject_dn="CN=Root PL,O=Test,C=US",
        key_size=2048,
        valid_days=365,
        path_length=3,
    )
    assert ca.path_length == 3

    cert = x509.load_pem_x509_certificate(ca.certificate.encode("utf-8"))
    bc = cert.extensions.get_extension_for_class(x509.BasicConstraints).value
    assert bc.ca is True
    assert bc.path_length == 3


@pytest.mark.asyncio
async def test_create_intermediate_ca(db: AsyncSession, root_ca: CertificateAuthority):
    """Create an intermediate CA signed by a parent."""
    ca_service = CAService(db)
    intermediate = await ca_service.create_ca(
        name="Intermediate CA",
        subject_dn="CN=Intermediate CA,O=Test Organization,C=US",
        key_size=2048,
        valid_days=1825,
        parent_ca_id=root_ca.id,
    )
    assert intermediate.id is not None
    assert intermediate.parent_ca_id == root_ca.id


@pytest.mark.asyncio
async def test_intermediate_issuer_matches_parent_subject(
    db: AsyncSession, root_ca: CertificateAuthority
):
    """The intermediate cert's issuer should match the parent's subject."""
    ca_service = CAService(db)
    intermediate = await ca_service.create_ca(
        name="Intermediate CA",
        subject_dn="CN=Intermediate CA,O=Test Organization,C=US",
        key_size=2048,
        valid_days=1825,
        parent_ca_id=root_ca.id,
    )
    parent_cert = x509.load_pem_x509_certificate(root_ca.certificate.encode("utf-8"))
    child_cert = x509.load_pem_x509_certificate(
        intermediate.certificate.encode("utf-8")
    )
    assert child_cert.issuer == parent_cert.subject


@pytest.mark.asyncio
async def test_intermediate_authority_key_identifier(
    db: AsyncSession, root_ca: CertificateAuthority
):
    """The intermediate cert's AKI should match the parent's SKI."""
    ca_service = CAService(db)
    intermediate = await ca_service.create_ca(
        name="Intermediate CA",
        subject_dn="CN=Intermediate CA,O=Test Organization,C=US",
        key_size=2048,
        valid_days=1825,
        parent_ca_id=root_ca.id,
    )
    parent_cert = x509.load_pem_x509_certificate(root_ca.certificate.encode("utf-8"))
    child_cert = x509.load_pem_x509_certificate(
        intermediate.certificate.encode("utf-8")
    )
    parent_ski = parent_cert.extensions.get_extension_for_class(
        x509.SubjectKeyIdentifier
    ).value
    child_aki = child_cert.extensions.get_extension_for_class(
        x509.AuthorityKeyIdentifier
    ).value
    assert child_aki.key_identifier == parent_ski.digest


@pytest.mark.asyncio
async def test_intermediate_ca_can_sign_leaf_certs(
    db: AsyncSession, root_ca: CertificateAuthority
):
    """An intermediate CA should be able to sign leaf certificates."""
    ca_service = CAService(db)
    intermediate = await ca_service.create_ca(
        name="Signing Intermediate",
        subject_dn="CN=Signing Intermediate,O=Test Organization,C=US",
        key_size=2048,
        valid_days=1825,
        parent_ca_id=root_ca.id,
    )
    cert_service = CertificateService(db)
    cert = await cert_service.create_certificate(
        ca_id=intermediate.id,
        common_name="leaf.example.com",
        subject_dn="CN=leaf.example.com,O=Test Organization,C=US",
        certificate_type=CertificateType.SERVER,
        key_size=2048,
        valid_days=365,
    )
    assert cert.id is not None
    assert cert.issuer_id == intermediate.id


@pytest.mark.asyncio
async def test_path_length_zero_prevents_sub_cas(
    db: AsyncSession, root_ca: CertificateAuthority
):
    """A CA with path_length=0 cannot create sub-CAs."""
    ca_service = CAService(db)
    intermediate = await ca_service.create_ca(
        name="Leaf Intermediate",
        subject_dn="CN=Leaf Intermediate,O=Test Organization,C=US",
        key_size=2048,
        valid_days=1825,
        parent_ca_id=root_ca.id,
        path_length=0,
    )
    with pytest.raises(ValueError, match="does not allow sub-CAs"):
        await ca_service.create_ca(
            name="Should Fail",
            subject_dn="CN=Should Fail,O=Test Organization,C=US",
            key_size=2048,
            valid_days=365,
            parent_ca_id=intermediate.id,
        )


@pytest.mark.asyncio
async def test_path_length_auto_decrements(
    db: AsyncSession, root_ca_with_path_length: CertificateAuthority
):
    """Path length auto-decrements: parent=2 -> child=1 -> grandchild=0 -> great-grandchild rejected."""
    ca_service = CAService(db)
    root = root_ca_with_path_length

    # Root has path_length=2
    assert root.path_length == 2

    # Child should auto-decrement to 1
    child = await ca_service.create_ca(
        name="Child CA",
        subject_dn="CN=Child CA,O=Test Organization,C=US",
        key_size=2048,
        valid_days=1825,
        parent_ca_id=root.id,
    )
    assert child.path_length == 1

    # Grandchild should auto-decrement to 0
    grandchild = await ca_service.create_ca(
        name="Grandchild CA",
        subject_dn="CN=Grandchild CA,O=Test Organization,C=US",
        key_size=2048,
        valid_days=1825,
        parent_ca_id=child.id,
    )
    assert grandchild.path_length == 0

    # Great-grandchild should be rejected (path_length=0 on grandchild)
    with pytest.raises(ValueError, match="does not allow sub-CAs"):
        await ca_service.create_ca(
            name="Great-Grandchild CA",
            subject_dn="CN=Great-Grandchild CA,O=Test Organization,C=US",
            key_size=2048,
            valid_days=365,
            parent_ca_id=grandchild.id,
        )


@pytest.mark.asyncio
async def test_user_path_length_exceeding_parent_rejected(
    db: AsyncSession, root_ca_with_path_length: CertificateAuthority
):
    """User-specified path_length exceeding parent's constraint is rejected."""
    ca_service = CAService(db)
    # Root has path_length=2, so child max is 1
    with pytest.raises(ValueError, match="exceeds maximum"):
        await ca_service.create_ca(
            name="Bad Child",
            subject_dn="CN=Bad Child,O=Test Organization,C=US",
            key_size=2048,
            valid_days=365,
            parent_ca_id=root_ca_with_path_length.id,
            path_length=5,
        )


@pytest.mark.asyncio
async def test_nonexistent_parent_ca_rejected(db: AsyncSession):
    """Referencing a nonexistent parent_ca_id raises ValueError."""
    ca_service = CAService(db)
    with pytest.raises(ValueError, match="not found"):
        await ca_service.create_ca(
            name="Orphan",
            subject_dn="CN=Orphan,O=Test Organization,C=US",
            key_size=2048,
            valid_days=365,
            parent_ca_id=99999,
        )


@pytest.mark.asyncio
async def test_get_ca_chain_root(db: AsyncSession, root_ca: CertificateAuthority):
    """Chain for a root CA is just itself."""
    ca_service = CAService(db)
    chain = await ca_service.get_ca_chain(root_ca.id)
    assert len(chain) == 1
    assert chain[0].id == root_ca.id


@pytest.mark.asyncio
async def test_get_ca_chain_two_levels(db: AsyncSession, root_ca: CertificateAuthority):
    """Chain for intermediate -> root has two entries."""
    ca_service = CAService(db)
    intermediate = await ca_service.create_ca(
        name="Chain Intermediate",
        subject_dn="CN=Chain Intermediate,O=Test Organization,C=US",
        key_size=2048,
        valid_days=1825,
        parent_ca_id=root_ca.id,
    )
    chain = await ca_service.get_ca_chain(intermediate.id)
    assert len(chain) == 2
    assert chain[0].id == intermediate.id
    assert chain[1].id == root_ca.id


@pytest.mark.asyncio
async def test_get_ca_chain_three_levels(
    db: AsyncSession, root_ca_with_path_length: CertificateAuthority
):
    """Three-level chain works correctly."""
    ca_service = CAService(db)
    root = root_ca_with_path_length

    child = await ca_service.create_ca(
        name="L1 CA",
        subject_dn="CN=L1 CA,O=Test Organization,C=US",
        key_size=2048,
        valid_days=1825,
        parent_ca_id=root.id,
    )
    grandchild = await ca_service.create_ca(
        name="L2 CA",
        subject_dn="CN=L2 CA,O=Test Organization,C=US",
        key_size=2048,
        valid_days=1825,
        parent_ca_id=child.id,
    )

    chain = await ca_service.get_ca_chain(grandchild.id)
    assert len(chain) == 3
    assert chain[0].id == grandchild.id
    assert chain[1].id == child.id
    assert chain[2].id == root.id


@pytest.mark.asyncio
async def test_delete_ca_with_children_raises(
    db: AsyncSession, root_ca: CertificateAuthority
):
    """Deleting a CA with child CAs raises HasDependentsError."""
    ca_service = CAService(db)
    await ca_service.create_ca(
        name="Child CA",
        subject_dn="CN=Child CA,O=Test Organization,C=US",
        key_size=2048,
        valid_days=1825,
        parent_ca_id=root_ca.id,
    )
    with pytest.raises(HasDependentsError):
        await ca_service.delete_ca(root_ca.id)


@pytest.mark.asyncio
async def test_delete_leaf_ca_succeeds(db: AsyncSession, root_ca: CertificateAuthority):
    """Deleting a CA with no children succeeds."""
    ca_service = CAService(db)
    intermediate = await ca_service.create_ca(
        name="Deleteable",
        subject_dn="CN=Deleteable,O=Test Organization,C=US",
        key_size=2048,
        valid_days=1825,
        parent_ca_id=root_ca.id,
    )
    result = await ca_service.delete_ca(intermediate.id)
    assert result is True
    assert await ca_service.get_ca(intermediate.id) is None


@pytest.mark.asyncio
async def test_get_child_cas(db: AsyncSession, root_ca: CertificateAuthority):
    """get_child_cas returns direct children only."""
    ca_service = CAService(db)
    child1 = await ca_service.create_ca(
        name="Child 1",
        subject_dn="CN=Child 1,O=Test Organization,C=US",
        key_size=2048,
        valid_days=1825,
        parent_ca_id=root_ca.id,
    )
    child2 = await ca_service.create_ca(
        name="Child 2",
        subject_dn="CN=Child 2,O=Test Organization,C=US",
        key_size=2048,
        valid_days=1825,
        parent_ca_id=root_ca.id,
    )

    children = await ca_service.get_child_cas(root_ca.id)
    child_ids = {c.id for c in children}
    assert child1.id in child_ids
    assert child2.id in child_ids
    assert len(children) == 2


@pytest.mark.asyncio
async def test_creating_intermediate_auto_disables_parent_leaf_certs(
    db: AsyncSession, root_ca: CertificateAuthority
):
    """Creating an intermediate CA sets parent's allow_leaf_certs to False."""
    assert root_ca.allow_leaf_certs is True

    ca_service = CAService(db)
    await ca_service.create_ca(
        name="Child CA",
        subject_dn="CN=Child CA,O=Test Organization,C=US",
        key_size=2048,
        valid_days=1825,
        parent_ca_id=root_ca.id,
    )

    await db.refresh(root_ca)
    assert root_ca.allow_leaf_certs is False


@pytest.mark.asyncio
async def test_leaf_cert_blocked_when_allow_leaf_certs_false(
    db: AsyncSession, root_ca: CertificateAuthority
):
    """Issuing a leaf cert from a CA with allow_leaf_certs=False raises LeafCertNotAllowedError."""
    ca_service = CAService(db)
    await ca_service.create_ca(
        name="Child CA",
        subject_dn="CN=Child CA,O=Test Organization,C=US",
        key_size=2048,
        valid_days=1825,
        parent_ca_id=root_ca.id,
    )

    cert_service = CertificateService(db)
    with pytest.raises(
        LeafCertNotAllowedError, match="does not allow leaf certificate"
    ):
        await cert_service.create_certificate(
            ca_id=root_ca.id,
            common_name="leaf.example.com",
            subject_dn="CN=leaf.example.com,O=Test Organization,C=US",
            certificate_type=CertificateType.SERVER,
            key_size=2048,
            valid_days=365,
        )


@pytest.mark.asyncio
async def test_intermediate_with_no_children_allows_leaf_certs(
    db: AsyncSession, root_ca: CertificateAuthority
):
    """An intermediate CA with no children can still issue leaf certs."""
    ca_service = CAService(db)
    intermediate = await ca_service.create_ca(
        name="Intermediate CA",
        subject_dn="CN=Intermediate CA,O=Test Organization,C=US",
        key_size=2048,
        valid_days=1825,
        parent_ca_id=root_ca.id,
    )
    assert intermediate.allow_leaf_certs is True

    cert_service = CertificateService(db)
    cert = await cert_service.create_certificate(
        ca_id=intermediate.id,
        common_name="leaf.example.com",
        subject_dn="CN=leaf.example.com,O=Test Organization,C=US",
        certificate_type=CertificateType.SERVER,
        key_size=2048,
        valid_days=365,
    )
    assert cert.id is not None


@pytest.mark.asyncio
async def test_explicit_allow_leaf_certs_override_on_ca_creation(
    db: AsyncSession,
):
    """User can explicitly set allow_leaf_certs=True on CA creation to override."""
    ca_service = CAService(db)
    root = await ca_service.create_ca(
        name="Root CA",
        subject_dn="CN=Root CA,O=Test Organization,C=US",
        key_size=2048,
        valid_days=3650,
        allow_leaf_certs=False,
    )
    assert root.allow_leaf_certs is False


@pytest.mark.asyncio
async def test_new_ca_defaults_allow_leaf_certs_true(db: AsyncSession):
    """A new CA defaults to allow_leaf_certs=True."""
    ca_service = CAService(db)
    ca = await ca_service.create_ca(
        name="Default CA",
        subject_dn="CN=Default CA,O=Test Organization,C=US",
        key_size=2048,
        valid_days=3650,
    )
    assert ca.allow_leaf_certs is True
